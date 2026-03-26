import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Tuple

from models import (
    AllocationRun,
    AllocationRunEntry,
    ConcurrencyAllocationSettings,
    ConcurrencyHistory,
    PartnerConfig,
    TierWeights,
)
from services.ssh_connection import SSHConnectionService

logger = logging.getLogger(__name__)

DEFAULT_SETTINGS = ConcurrencyAllocationSettings()
SETTINGS_KEY = "concurrency_allocation"


class ConcurrencyAllocator:
    def __init__(self, db, ssh_service: SSHConnectionService):
        self.db = db
        self.ssh_service = ssh_service

    # ------------------------------------------------------------------
    # Public entry point — called by scheduler after every data fetch
    # ------------------------------------------------------------------

    async def run_allocation_cycle(self) -> AllocationRun:
        """Run one full allocation cycle and write limits to all clients."""
        logger.info("Starting concurrency allocation cycle")

        settings = await self._load_settings()
        partners = await self._load_active_partners()
        snapshots = await self._load_latest_snapshots([p.id for p in partners])

        total_in_flight = sum(
            snapshots.get(p.id, {}).get("activeCalls", 0)
            + snapshots.get(p.id, {}).get("queuedCalls", 0)
            for p in partners
        )

        available = settings.globalMaxConcurrency - total_in_flight

        if not partners:
            run = AllocationRun(
                globalMax=settings.globalMaxConcurrency,
                totalInFlight=total_in_flight,
                availableSlots=max(available, 0),
                status="no_active_clients",
            )
            await self._save_run(run)
            return run

        if available <= 0:
            run = await self._apply_saturated_floor(
                partners, snapshots, settings, total_in_flight
            )
            await self._save_run(run)
            return run

        allocations = self._compute_allocations(
            partners, snapshots, settings, available
        )
        await self._write_allocations(partners, snapshots, allocations, settings)

        run = AllocationRun(
            globalMax=settings.globalMaxConcurrency,
            totalInFlight=total_in_flight,
            availableSlots=available,
            status="normal",
            allocations=allocations,
        )
        await self._save_run(run)
        logger.info(
            f"Allocation cycle complete — {len(allocations)} clients updated, "
            f"available={available}, in-flight={total_in_flight}"
        )
        return run

    # ------------------------------------------------------------------
    # Core algorithm
    # ------------------------------------------------------------------

    def _compute_allocations(
        self,
        partners: List[PartnerConfig],
        snapshots: Dict,
        settings: ConcurrencyAllocationSettings,
        available: int,
    ) -> List[AllocationRunEntry]:
        weights = {
            1: settings.tierWeights.p1,
            2: settings.tierWeights.p2,
            3: settings.tierWeights.p3,
            4: settings.tierWeights.p4,
        }

        # Group partners by priority — only include those with demand and not paused
        tier_clients: Dict[int, List[PartnerConfig]] = {1: [], 2: [], 3: [], 4: []}
        for p in partners:
            snap = snapshots.get(p.id, {})
            remaining = snap.get("remainingCalls", 0)
            raw_paused = snap.get("pauseAllCampaigns", False)
            paused = raw_paused if isinstance(raw_paused, bool) else str(raw_paused).strip().lower() in ("1", "true", "yes")
            if remaining > 0 and not paused:
                tier_clients[p.priority].append(p)

        # Compute tier pools based on active tiers only (renormalize)
        tier_pools = self._compute_tier_pools(tier_clients, weights, available)

        # Assign slots within each tier (equal split + maxConcurrency cap + surplus cascade)
        allocations = self._assign_within_tiers(
            tier_clients, tier_pools, weights, snapshots, settings, available
        )

        # Handle partners with 0 demand — give them the floor
        allocated_ids = {a.partnerId for a in allocations}
        for p in partners:
            if p.id not in allocated_ids:
                snap = snapshots.get(p.id, {})
                allocations.append(
                    AllocationRunEntry(
                        partnerId=p.id,
                        partnerName=p.partnerName,
                        priority=p.priority,
                        tierPool=0,
                        maxConcurrency=p.maxConcurrency,
                        oldLimit=p.concurrencyLimit,
                        newLimit=settings.minConcurrencyPerClient,
                        remainingContacts=snap.get("remainingCalls", 0),
                        activeCalls=snap.get("activeCalls", 0),
                    )
                )

        return allocations

    def _compute_tier_pools(
        self,
        tier_clients: Dict[int, List[PartnerConfig]],
        weights: Dict[int, int],
        available: int,
    ) -> Dict[int, float]:
        active_tiers = {t for t, clients in tier_clients.items() if clients}
        total_weight = sum(weights[t] for t in active_tiers)
        if total_weight == 0:
            return {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
        return {
            t: (weights[t] / total_weight) * available if t in active_tiers else 0.0
            for t in weights
        }

    def _assign_within_tiers(
        self,
        tier_clients: Dict[int, List[PartnerConfig]],
        tier_pools: Dict[int, float],
        weights: Dict[int, int],
        snapshots: Dict,
        settings: ConcurrencyAllocationSettings,
        available: int,
    ) -> List[AllocationRunEntry]:
        # Build mutable allocation map: partner_id -> float slots
        alloc: Dict[str, float] = {}
        partner_map: Dict[str, PartnerConfig] = {}

        for tier, clients in tier_clients.items():
            if not clients:
                continue
            pool = tier_pools[tier]
            per_client = pool / len(clients)

            for p in clients:
                partner_map[p.id] = p
                alloc[p.id] = per_client

        # Apply maxConcurrency caps and cascade surplus
        alloc = self._cascade_surplus(alloc, partner_map, tier_clients, weights, tier_pools)

        # Floor and distribute remainder
        alloc = self._apply_floor_and_remainder(alloc, partner_map, snapshots)

        # Build result entries
        entries: List[AllocationRunEntry] = []
        for pid, slots in alloc.items():
            p = partner_map[pid]
            snap = snapshots.get(pid, {})
            active_calls = snap.get("activeCalls", 0)
            queued_calls = snap.get("queuedCalls", 0)
            raw_new_limit = active_calls + queued_calls + int(slots)
            new_limit = max(raw_new_limit, settings.minConcurrencyPerClient)
            new_limit = min(new_limit, p.maxConcurrency)

            entries.append(
                AllocationRunEntry(
                    partnerId=pid,
                    partnerName=p.partnerName,
                    priority=p.priority,
                    tierPool=tier_pools[p.priority],
                    maxConcurrency=p.maxConcurrency,
                    oldLimit=p.concurrencyLimit,
                    newLimit=new_limit,
                    remainingContacts=snap.get("remainingCalls", 0),
                    activeCalls=active_calls,
                )
            )
        return entries

    def _cascade_surplus(
        self,
        alloc: Dict[str, float],
        partner_map: Dict[str, PartnerConfig],
        tier_clients: Dict[int, List[PartnerConfig]],
        weights: Dict[int, int],
        tier_pools: Dict[int, float],
    ) -> Dict[str, float]:
        """
        Cap allocations at maxConcurrency. Surplus cascades:
          1. Within the same tier first (redistribute equally to uncapped clients)
          2. Then cross-tier by weight ratio
        Iterates until no more surplus moves.
        """
        for _ in range(10):  # max iterations to prevent infinite loops
            surplus = 0.0
            capped_ids = set()

            for pid, slots in alloc.items():
                cap = partner_map[pid].maxConcurrency
                if slots > cap:
                    surplus += slots - cap
                    alloc[pid] = float(cap)
                    capped_ids.add(pid)

            if surplus < 0.01:
                break

            # Step 1: redistribute within tiers
            surplus = self._redistribute_within_tiers(
                alloc, partner_map, tier_clients, capped_ids, surplus
            )

            # Step 2: redistribute cross-tier if still surplus
            if surplus >= 0.01:
                self._redistribute_cross_tier(
                    alloc, partner_map, tier_clients, weights, capped_ids, surplus
                )

        return alloc

    def _redistribute_within_tiers(
        self,
        alloc: Dict[str, float],
        partner_map: Dict[str, PartnerConfig],
        tier_clients: Dict[int, List[PartnerConfig]],
        capped_ids: set,
        surplus: float,
    ) -> float:
        remaining_surplus = surplus
        for tier, clients in tier_clients.items():
            uncapped = [
                p for p in clients
                if p.id not in capped_ids and alloc.get(p.id, 0) < p.maxConcurrency
            ]
            if not uncapped:
                continue
            # Collect surplus only from this tier's capped clients
            tier_surplus = sum(
                0.0 for p in clients if p.id in capped_ids
            )
            if tier_surplus <= 0:
                continue
            share = tier_surplus / len(uncapped)
            for p in uncapped:
                alloc[p.id] = alloc.get(p.id, 0) + share
            remaining_surplus -= tier_surplus
        return max(remaining_surplus, 0.0)

    def _redistribute_cross_tier(
        self,
        alloc: Dict[str, float],
        partner_map: Dict[str, PartnerConfig],
        tier_clients: Dict[int, List[PartnerConfig]],
        weights: Dict[int, int],
        capped_ids: set,
        surplus: float,
    ) -> None:
        eligible: List[Tuple[int, PartnerConfig]] = [
            (tier, p)
            for tier, clients in tier_clients.items()
            for p in clients
            if p.id not in capped_ids and alloc.get(p.id, 0) < p.maxConcurrency
        ]
        if not eligible:
            return
        total_weight = sum(weights[tier] for tier, _ in eligible)
        if total_weight == 0:
            return
        for tier, p in eligible:
            share = (weights[tier] / total_weight) * surplus
            alloc[p.id] = alloc.get(p.id, 0) + share

    def _apply_floor_and_remainder(
        self,
        alloc: Dict[str, float],
        partner_map: Dict[str, PartnerConfig],
        snapshots: Dict,
    ) -> Dict[str, float]:
        """Floor all allocations. Give remainder slots 1-by-1 to highest demand clients."""
        floored = {pid: float(int(slots)) for pid, slots in alloc.items()}
        total_floored = sum(floored.values())
        total_raw = sum(alloc.values())
        remainder = int(round(total_raw - total_floored))

        if remainder > 0:
            # Sort by remainingContacts DESC to assign remainder
            sorted_ids = sorted(
                floored.keys(),
                key=lambda pid: snapshots.get(pid, {}).get("remainingCalls", 0),
                reverse=True,
            )
            for i in range(min(remainder, len(sorted_ids))):
                floored[sorted_ids[i]] += 1.0

        return floored

    # ------------------------------------------------------------------
    # Saturated path
    # ------------------------------------------------------------------

    async def _apply_saturated_floor(
        self,
        partners: List[PartnerConfig],
        snapshots: Dict,
        settings: ConcurrencyAllocationSettings,
        total_in_flight: int,
    ) -> AllocationRun:
        logger.warning(
            f"System saturated — in-flight={total_in_flight} >= globalMax={settings.globalMaxConcurrency}. "
            f"Writing floor={settings.minConcurrencyPerClient} to all clients."
        )
        floor = settings.minConcurrencyPerClient
        allocations = []
        for p in partners:
            snap = snapshots.get(p.id, {})
            new_limit = min(floor, p.maxConcurrency)
            sync_result = await self._write_single(p, new_limit, "auto_allocation_saturated")
            allocations.append(
                AllocationRunEntry(
                    partnerId=p.id,
                    partnerName=p.partnerName,
                    priority=p.priority,
                    tierPool=0,
                    maxConcurrency=p.maxConcurrency,
                    oldLimit=p.concurrencyLimit,
                    newLimit=new_limit,
                    remainingContacts=snap.get("remainingCalls", 0),
                    activeCalls=snap.get("activeCalls", 0),
                    syncedToPartner=sync_result["success"],
                    syncError=sync_result.get("error"),
                )
            )
        return AllocationRun(
            globalMax=settings.globalMaxConcurrency,
            totalInFlight=total_in_flight,
            availableSlots=0,
            status="saturated",
            allocations=allocations,
        )

    # ------------------------------------------------------------------
    # Write helpers
    # ------------------------------------------------------------------

    async def _write_allocations(
        self,
        partners: List[PartnerConfig],
        snapshots: Dict,
        allocations: List[AllocationRunEntry],
        settings: ConcurrencyAllocationSettings,
    ) -> None:
        alloc_map = {a.partnerId: a for a in allocations}
        for p in partners:
            entry = alloc_map.get(p.id)
            new_limit = entry.newLimit if entry else settings.minConcurrencyPerClient
            sync_result = await self._write_single(p, new_limit, "auto_allocation")
            if entry:
                entry.syncedToPartner = sync_result["success"]
                entry.syncError = sync_result.get("error")

    async def _write_single(
        self, partner: PartnerConfig, new_limit: int, reason: str
    ) -> dict:
        """Write new limit to MongoDB + partner MySQL. Returns sync result dict."""
        sync_result = {"success": False, "error": "write not attempted"}
        try:
            old_limit = partner.concurrencyLimit

            # Update admin MongoDB
            await self.db.partner_configs.update_one(
                {"id": partner.id},
                {
                    "$set": {
                        "concurrencyLimit": new_limit,
                        "updatedAt": datetime.now(timezone.utc).isoformat(),
                    }
                },
            )

            # Log to concurrency history
            history_id = str(uuid.uuid4())
            history = ConcurrencyHistory(
                id=history_id,
                partnerId=partner.id,
                oldLimit=old_limit,
                newLimit=new_limit,
                reason=reason,
                changedBy="auto_allocator",
            )
            history_dict = history.model_dump()
            history_dict["changedAt"] = history_dict["changedAt"].isoformat()
            await self.db.concurrency_history.insert_one(history_dict)

            # Sync to partner MySQL via SSH
            sync_result = await self._sync_to_partner_db(partner, new_limit, old_limit)

            # Update history record with sync outcome
            await self.db.concurrency_history.update_one(
                {"id": history_id},
                {
                    "$set": {
                        "syncedToPartner": sync_result["success"],
                        "syncError": sync_result.get("error"),
                        "syncedAt": datetime.now(timezone.utc).isoformat() if sync_result["success"] else None,
                    }
                },
            )

        except Exception as e:
            logger.error(
                f"Failed to write concurrency limit for {partner.partnerName}: {e}"
            )
            sync_result = {"success": False, "error": str(e)}

        return sync_result

    async def _sync_to_partner_db(
        self, partner: PartnerConfig, new_limit: int, old_limit: int
    ) -> dict:
        """Sync concurrency limit to partner MySQL. Returns {success, error}."""
        try:
            # First verify the setting row exists
            check_query = "SELECT value FROM settings WHERE name = 'callConcurrency'"
            rows = await self.ssh_service.execute_query(partner, check_query)
            if not rows:
                msg = f"callConcurrency setting does not exist in {partner.partnerName}"
                logger.warning(msg)
                return {"success": False, "error": msg}

            current_value = int(rows[0].get("value", 0))
            if current_value == new_limit:
                logger.info(
                    f"Concurrency already {new_limit} in {partner.partnerName}, no update needed"
                )
                return {"success": True}

            update_query = "UPDATE settings SET value = %s WHERE name = 'callConcurrency'"
            await self.ssh_service.execute_update(
                partner, update_query, (new_limit,)
            )
            try:
                audit_query = (
                    "INSERT INTO settings_auditlogs (userid, oldvalue, newvalue, createdat) "
                    "VALUES (9999999999, %s, %s, NOW())"
                )
                await self.ssh_service.execute_update(
                    partner, audit_query, (old_limit, new_limit)
                )
            except Exception:
                pass  # audit log failure is non-fatal
            logger.info(
                f"Synced concurrency {new_limit} to partner {partner.partnerName}"
            )
            return {"success": True}
        except Exception as e:
            logger.error(f"SSH sync failed for {partner.partnerName}: {e}")
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Settings helpers
    # ------------------------------------------------------------------

    async def _load_settings(self) -> ConcurrencyAllocationSettings:
        try:
            doc = await self.db.settings.find_one(
                {"key": SETTINGS_KEY}, {"_id": 0}
            )
            if doc and "value" in doc:
                return ConcurrencyAllocationSettings(**doc["value"])
        except Exception as e:
            logger.warning(f"Could not load allocation settings, using defaults: {e}")
        return DEFAULT_SETTINGS

    async def save_settings(self, settings: ConcurrencyAllocationSettings) -> None:
        await self.db.settings.update_one(
            {"key": SETTINGS_KEY},
            {"$set": {"key": SETTINGS_KEY, "value": settings.model_dump()}},
            upsert=True,
        )

    # ------------------------------------------------------------------
    # Data loaders
    # ------------------------------------------------------------------

    async def _load_active_partners(self) -> List[PartnerConfig]:
        docs = await self.db.partner_configs.find(
            {"isActive": True}, {"_id": 0}
        ).to_list(1000)
        return [PartnerConfig(**d) for d in docs]

    async def _load_latest_snapshots(self, partner_ids: List[str]) -> Dict:
        """Returns dict of partner_id -> latest snapshot fields."""
        snapshots = {}
        for pid in partner_ids:
            doc = await self.db.dashboard_snapshots.find_one(
                {"partnerId": pid},
                {"_id": 0, "activeCalls": 1, "queuedCalls": 1, "remainingCalls": 1, "pauseAllCampaigns": 1},
                sort=[("snapshotTime", -1)],
            )
            snapshots[pid] = doc or {}
        return snapshots

    async def _save_run(self, run: AllocationRun) -> None:
        try:
            run_dict = run.model_dump()
            run_dict["runAt"] = run_dict["runAt"].isoformat()
            await self.db.allocation_runs.insert_one(run_dict)
        except Exception as e:
            logger.error(f"Failed to save allocation run: {e}")

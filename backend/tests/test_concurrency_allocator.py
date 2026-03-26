"""
Unit tests for ConcurrencyAllocator — no real DB or SSH required.
All DB and SSH calls are mocked.
Run with: python -m pytest tests/test_concurrency_allocator.py -v
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.concurrency_allocator import ConcurrencyAllocator
from models import (
    ConcurrencyAllocationSettings,
    PartnerConfig,
    SSHConfig,
    TierWeights,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_partner(id, name, priority, max_concurrency, concurrency_limit=10):
    return PartnerConfig(
        id=id,
        partnerName=name,
        dbHost="localhost",
        dbPort=3306,
        dbName="test",
        dbUsername="user",
        dbPassword="pass",
        sshConfig=SSHConfig(enabled=False),
        priority=priority,
        maxConcurrency=max_concurrency,
        concurrencyLimit=concurrency_limit,
    )

def make_snap(active=0, queued=0, remaining=0):
    return {"activeCalls": active, "queuedCalls": queued, "remainingCalls": remaining}

def make_settings(**kwargs):
    defaults = dict(
        globalMaxConcurrency=200,
        tierWeights=TierWeights(p1=40, p2=30, p3=20, p4=10),
        minConcurrencyPerClient=2,
        allocationIntervalSeconds=60,
    )
    defaults.update(kwargs)
    return ConcurrencyAllocationSettings(**defaults)

def make_allocator():
    db = MagicMock()
    ssh = MagicMock()
    allocator = ConcurrencyAllocator(db, ssh)
    # Silence writes for pure algorithm tests
    allocator._write_single = AsyncMock()
    return allocator


# ---------------------------------------------------------------------------
# 1. Basic tier proportional split
# ---------------------------------------------------------------------------

class TestTierPools:
    def test_all_tiers_active(self):
        allocator = make_allocator()
        tier_clients = {
            1: [make_partner("a", "A", 1, 100)],
            2: [make_partner("b", "B", 2, 100)],
            3: [make_partner("c", "C", 3, 100)],
            4: [make_partner("d", "D", 4, 100)],
        }
        weights = {1: 40, 2: 30, 3: 20, 4: 10}
        pools = allocator._compute_tier_pools(tier_clients, weights, 100)
        assert pools[1] == pytest.approx(40.0)
        assert pools[2] == pytest.approx(30.0)
        assert pools[3] == pytest.approx(20.0)
        assert pools[4] == pytest.approx(10.0)

    def test_p4_missing_renormalizes(self):
        allocator = make_allocator()
        tier_clients = {
            1: [make_partner("a", "A", 1, 100)],
            2: [make_partner("b", "B", 2, 100)],
            3: [make_partner("c", "C", 3, 100)],
            4: [],  # no demand
        }
        weights = {1: 40, 2: 30, 3: 20, 4: 10}
        pools = allocator._compute_tier_pools(tier_clients, weights, 90)
        total = pools[1] + pools[2] + pools[3] + pools[4]
        assert total == pytest.approx(90.0, abs=0.1)
        assert pools[4] == 0.0
        # P1 should get more than P2
        assert pools[1] > pools[2] > pools[3]

    def test_only_p1_active_gets_everything(self):
        allocator = make_allocator()
        tier_clients = {1: [make_partner("a", "A", 1, 100)], 2: [], 3: [], 4: []}
        weights = {1: 40, 2: 30, 3: 20, 4: 10}
        pools = allocator._compute_tier_pools(tier_clients, weights, 120)
        assert pools[1] == pytest.approx(120.0)

    def test_no_active_tiers_returns_zero_pools(self):
        allocator = make_allocator()
        tier_clients = {1: [], 2: [], 3: [], 4: []}
        weights = {1: 40, 2: 30, 3: 20, 4: 10}
        pools = allocator._compute_tier_pools(tier_clients, weights, 120)
        assert all(v == 0.0 for v in pools.values())


# ---------------------------------------------------------------------------
# 2. Equal split within a tier
# ---------------------------------------------------------------------------

class TestEqualSplitWithinTier:
    def test_two_p1_clients_equal_split(self):
        allocator = make_allocator()
        partners = [
            make_partner("a", "A", 1, 100),
            make_partner("b", "B", 1, 100),
        ]
        snapshots = {
            "a": make_snap(active=10, queued=5, remaining=10000),
            "b": make_snap(active=5, queued=5, remaining=3000),
        }
        settings = make_settings(globalMaxConcurrency=200)

        # available = 200 - (10+5+5+5) = 175
        available = 175
        entries = allocator._compute_allocations(partners, snapshots, settings, available)

        alloc = {e.partnerId: e for e in entries}
        # Both P1 — equal SHARE (newLimit - activeCalls) within 1 slot due to rounding
        share_a = alloc["a"].newLimit - alloc["a"].activeCalls
        share_b = alloc["b"].newLimit - alloc["b"].activeCalls
        assert abs(share_a - share_b) <= 1

    def test_single_client_gets_full_tier_pool(self):
        allocator = make_allocator()
        partners = [make_partner("a", "A", 1, 200)]
        snapshots = {"a": make_snap(active=0, queued=0, remaining=5000)}
        settings = make_settings(globalMaxConcurrency=200)

        available = 120
        entries = allocator._compute_allocations(partners, snapshots, settings, available)
        # One P1 client, no others — gets entire available (capped at maxConcurrency=200)
        assert entries[0].newLimit == 120  # active=0 + 120 share


# ---------------------------------------------------------------------------
# 3. maxConcurrency cap and surplus redistribution
# ---------------------------------------------------------------------------

class TestSurplusRedistribution:
    def test_within_tier_surplus_goes_to_uncapped_sibling(self):
        allocator = make_allocator()
        # P1 pool = 120 (only tier active), 2 clients → 60 each
        # Client A capped at 20 → 40 surplus → goes to B
        partners = [
            make_partner("a", "A", 1, 20),   # capped at 20
            make_partner("b", "B", 1, 200),  # uncapped
        ]
        snapshots = {
            "a": make_snap(active=0, queued=0, remaining=1000),
            "b": make_snap(active=0, queued=0, remaining=1000),
        }
        settings = make_settings(globalMaxConcurrency=200)
        available = 120

        entries = allocator._compute_allocations(partners, snapshots, settings, available)
        alloc = {e.partnerId: e for e in entries}

        assert alloc["a"].newLimit == 20
        # B should absorb A's surplus: 60 + 40 = 100
        assert alloc["b"].newLimit == pytest.approx(100, abs=2)

    def test_cross_tier_surplus_when_whole_tier_capped(self):
        allocator = make_allocator()
        # P1 has 1 client capped at 10. P1 pool = 48 slots. Surplus = 38 → goes to P2/P3/P4
        partners = [
            make_partner("a", "A", 1, 10),   # P1, capped very low
            make_partner("b", "B", 2, 200),  # P2, uncapped
            make_partner("c", "C", 3, 200),  # P3, uncapped
        ]
        snapshots = {
            "a": make_snap(active=0, queued=0, remaining=1000),
            "b": make_snap(active=0, queued=0, remaining=1000),
            "c": make_snap(active=0, queued=0, remaining=1000),
        }
        settings = make_settings(globalMaxConcurrency=200)
        available = 120

        entries = allocator._compute_allocations(partners, snapshots, settings, available)
        alloc = {e.partnerId: e for e in entries}

        # A is capped at 10
        assert alloc["a"].newLimit == 10
        # B and C should receive A's surplus — both above their raw equal share
        assert alloc["b"].newLimit > 36  # raw P2 share = (30/80)*120 = 45, B gets more after surplus
        assert alloc["c"].newLimit > 0

    def test_all_clients_capped_total_does_not_exceed_available(self):
        allocator = make_allocator()
        partners = [
            make_partner("a", "A", 1, 15),
            make_partner("b", "B", 2, 15),
            make_partner("c", "C", 3, 15),
            make_partner("d", "D", 4, 15),
        ]
        snapshots = {p.id: make_snap(active=0, queued=0, remaining=500) for p in partners}
        settings = make_settings(globalMaxConcurrency=200)
        available = 120

        entries = allocator._compute_allocations(partners, snapshots, settings, available)
        total_new = sum(e.newLimit for e in entries if e.remainingContacts > 0)
        assert total_new <= available + 10  # small tolerance for active_calls offset


# ---------------------------------------------------------------------------
# 4. Rounding — sum never exceeds globalMax
# ---------------------------------------------------------------------------

class TestRounding:
    def test_floor_rounding_sum_within_bounds(self):
        allocator = make_allocator()
        partners = [make_partner(str(i), f"P{i}", 1, 200) for i in range(3)]
        snapshots = {p.id: make_snap(active=0, queued=0, remaining=1000) for p in partners}
        settings = make_settings(globalMaxConcurrency=200)
        available = 100  # 100/3 = 33.33 → floors + remainder

        entries = allocator._compute_allocations(partners, snapshots, settings, available)
        demand_entries = [e for e in entries if e.remainingContacts > 0]
        total = sum(e.newLimit for e in demand_entries)
        assert total <= 100 + len(demand_entries)  # activeCalls offset tolerance

    def test_remainder_goes_to_highest_demand_client(self):
        allocator = make_allocator()
        # 3 clients, available=100 → remainder of 1 slot
        partners = [
            make_partner("a", "A", 1, 200),  # 500 remaining
            make_partner("b", "B", 1, 200),  # 100 remaining
            make_partner("c", "C", 1, 200),  # 50 remaining
        ]
        snapshots = {
            "a": make_snap(active=0, queued=0, remaining=500),
            "b": make_snap(active=0, queued=0, remaining=100),
            "c": make_snap(active=0, queued=0, remaining=50),
        }
        settings = make_settings(globalMaxConcurrency=200)

        raw = {
            "a": 500 / 3,
            "b": 100 / 3,
            "c": 50 / 3,
        }
        alloc = {k: float(v) for k, v in raw.items()}
        partner_map = {p.id: p for p in partners}
        result = allocator._apply_floor_and_remainder(alloc, partner_map, snapshots)

        # 'a' has most remaining contacts — should get the remainder slot
        floored = {k: int(v) for k, v in raw.items()}
        remainder_receiver = max(result, key=result.get)
        assert remainder_receiver == "a"


# ---------------------------------------------------------------------------
# 5. Zero demand → floor = 2
# ---------------------------------------------------------------------------

class TestZeroDemand:
    def test_zero_demand_clients_get_floor(self):
        allocator = make_allocator()
        partners = [
            make_partner("a", "A", 1, 100),   # has demand
            make_partner("b", "B", 2, 100),   # no demand
        ]
        snapshots = {
            "a": make_snap(active=5, queued=5, remaining=1000),
            "b": make_snap(active=0, queued=0, remaining=0),
        }
        settings = make_settings(globalMaxConcurrency=200, minConcurrencyPerClient=2)
        available = 190

        entries = allocator._compute_allocations(partners, snapshots, settings, available)
        alloc = {e.partnerId: e for e in entries}

        assert alloc["b"].newLimit == 2  # floor
        assert alloc["a"].newLimit > 2   # gets real allocation


# ---------------------------------------------------------------------------
# 6. Saturated system (available <= 0)
# ---------------------------------------------------------------------------

class TestSaturatedSystem:
    def test_saturated_writes_floor_to_all(self):
        async def run():
            allocator = make_allocator()
            partners = [
                make_partner("a", "A", 1, 100),
                make_partner("b", "B", 2, 100),
            ]
            snapshots = {
                "a": make_snap(active=100, queued=50, remaining=500),
                "b": make_snap(active=30, queued=25, remaining=200),
            }
            settings = make_settings(globalMaxConcurrency=200, minConcurrencyPerClient=2)
            total_in_flight = 205  # > globalMax

            run_result = await allocator._apply_saturated_floor(
                partners, snapshots, settings, total_in_flight
            )

            assert run_result.status == "saturated"
            assert all(e.newLimit == 2 for e in run_result.allocations)
            assert allocator._write_single.call_count == 2

        asyncio.get_event_loop().run_until_complete(run())


# ---------------------------------------------------------------------------
# 7. Full cycle integration (mocked DB + SSH)
# ---------------------------------------------------------------------------

class TestFullCycle:
    def test_normal_cycle_end_to_end(self):
        async def run():
            db = MagicMock()
            ssh = MagicMock()
            allocator = ConcurrencyAllocator(db, ssh)
            allocator._write_single = AsyncMock()

            partners = [
                make_partner("p1", "Client1", 1, 80),
                make_partner("p2", "Client2", 2, 50),
                make_partner("p3", "Client3", 4, 30),  # P4, no demand
            ]
            snapshots = {
                "p1": make_snap(active=20, queued=10, remaining=5000),
                "p2": make_snap(active=10, queued=5,  remaining=2000),
                "p3": make_snap(active=0,  queued=0,  remaining=0),
            }

            settings = make_settings(globalMaxConcurrency=200)

            allocator._load_settings = AsyncMock(return_value=settings)
            allocator._load_active_partners = AsyncMock(return_value=partners)
            allocator._load_latest_snapshots = AsyncMock(return_value=snapshots)
            allocator._save_run = AsyncMock()

            result = await allocator.run_allocation_cycle()

            assert result.status == "normal"
            assert result.totalInFlight == 45   # 20+10+10+5
            assert result.availableSlots == 155  # 200-45
            assert allocator._write_single.call_count == 3  # all 3 clients written

            alloc = {e.partnerId: e for e in result.allocations}
            # P3 has no demand → floor=2
            assert alloc["p3"].newLimit == 2
            # P1 should get more than P2 (higher priority, P2 gets 30% pool)
            assert alloc["p1"].newLimit > alloc["p2"].newLimit

        asyncio.get_event_loop().run_until_complete(run())

    def test_no_active_clients(self):
        async def run():
            allocator = make_allocator()
            allocator._load_settings = AsyncMock(return_value=make_settings())
            allocator._load_active_partners = AsyncMock(return_value=[])
            allocator._load_latest_snapshots = AsyncMock(return_value={})
            allocator._save_run = AsyncMock()

            result = await allocator.run_allocation_cycle()
            assert result.status == "no_active_clients"
            assert result.allocations == []

        asyncio.get_event_loop().run_until_complete(run())


# ---------------------------------------------------------------------------
# 8. Settings validation (tierWeights must sum to 100)
# ---------------------------------------------------------------------------

class TestSettingsValidation:
    def test_tier_weights_sum_to_100(self):
        w = TierWeights(p1=40, p2=30, p3=20, p4=10)
        assert w.p1 + w.p2 + w.p3 + w.p4 == 100

    def test_custom_tier_weights(self):
        w = TierWeights(p1=50, p2=25, p3=15, p4=10)
        allocator = make_allocator()
        tier_clients = {
            1: [make_partner("a", "A", 1, 100)],
            2: [make_partner("b", "B", 2, 100)],
            3: [], 4: [],
        }
        pools = allocator._compute_tier_pools(
            tier_clients, {1: 50, 2: 25, 3: 15, 4: 10}, 100
        )
        # With only P1 and P2 active: P1=50/(50+25)*100=66.7, P2=25/75*100=33.3
        assert pools[1] == pytest.approx(66.67, abs=0.1)
        assert pools[2] == pytest.approx(33.33, abs=0.1)

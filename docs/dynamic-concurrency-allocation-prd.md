# PRD — Dynamic Concurrency Allocation

**Version:** 1.0
**Status:** Ready for Implementation

---

## 1. Overview

This feature introduces an automated system that dynamically allocates concurrent call slots across all active clients every 60 seconds. The goal is to ensure the global call capacity is always fully utilised, fairly distributed by client priority, and responsive to real-time demand.

---

## 2. Algorithm Explanation

### 2.1 Core Concept

There is a **global maximum concurrency** (e.g. 200 slots) — the ceiling on total simultaneous calls across all clients at any point in time. Every 60 seconds, the system:

1. Fetches fresh data from all partner databases (active calls, queued calls, remaining contacts)
2. Computes how many slots are currently free
3. Distributes those free slots across all clients based on priority tiers
4. Writes the new `concurrencyLimit` to every client

---

### 2.2 Available Concurrency

```
availableConcurrency = globalMax - SUM(activeCalls + queuedCalls across all clients)
```

This is the free headroom — slots not currently consumed or committed. The distribution algorithm always works from this number, not from globalMax itself.

**If availableConcurrency ≤ 0** (system fully saturated):
- Skip tier distribution entirely
- Write `minConcurrencyPerClient` (default: 2) to all active clients
- Log cycle as "saturated"
- Resume normal allocation next cycle

---

### 2.3 Priority Tiers

Every client is assigned a priority (1–4). The available concurrency is pre-divided into tier pools by configurable percentage weights:

| Priority | Default Weight | Example (120 available) |
|----------|---------------|--------------------------|
| P1       | 40%           | 48 slots                 |
| P2       | 30%           | 36 slots                 |
| P3       | 20%           | 24 slots                 |
| P4       | 10%           | 12 slots                 |

Weights must always sum to 100. They are fully configurable via API with no redeploy required.

---

### 2.4 Redistribution — Unused Tier Slots Flow to Active Tiers

If a tier has no clients with demand, its weight is removed and the remaining tiers are **renormalized** over the full available concurrency. Unused slots never go to waste.

**Example — P4 has no demand:**
```
Active tiers: P1(40) + P2(30) + P3(20) → total weight = 90
Renormalize over 120 available:

  P1 pool = (40/90) × 120 = 53 slots
  P2 pool = (30/90) × 120 = 40 slots
  P3 pool = (20/90) × 120 = 27 slots
```

**Example — Only P2 and P3 have demand:**
```
Active tiers: P2(30) + P3(20) → total weight = 50

  P2 pool = (30/50) × 120 = 72 slots
  P3 pool = (20/50) × 120 = 48 slots
```

---

### 2.5 Within-Tier Distribution — Equal Split

Within each tier, available slots are **divided equally** among all active clients in that tier regardless of their individual demand size. Two P1 clients each get exactly half of the P1 pool.

```
P1 pool = 53 slots, 2 P1 clients → 26 slots each (remainder handled per rule 2.7)
```

---

### 2.6 Per-Client maxConcurrency Cap and Surplus Redistribution

Each client has a `maxConcurrency` ceiling — the hard limit on how many concurrent calls they are allowed regardless of available pool size. This is a business configuration (e.g. a client has only subscribed to 30 concurrent calls).

When a client's equal share exceeds their `maxConcurrency`, the surplus is redistributed in order:

```
Step 1 → Redistribute surplus equally to remaining clients in the SAME tier
          (up to their own maxConcurrency)
Step 2 → If surplus remains after all tier clients are capped,
          redistribute to other active tiers by their weight ratio
Step 3 → Within those tiers, same equal split + maxConcurrency cap applies
Step 4 → Repeat until surplus = 0 or all active clients are at their maxConcurrency
```

---

### 2.7 Rounding

All allocations are **floored** to avoid the sum exceeding globalMax. Any remainder slots (1 or 2 due to rounding) are distributed one-by-one to clients with the highest `remainingContacts` first.

---

### 2.8 Final concurrencyLimit Written Per Client

Every cycle, every active client receives a write:

```
newConcurrencyLimit = client.currentActiveCalls + client.shareOfAvailable
newConcurrencyLimit = max(newConcurrencyLimit, minConcurrencyPerClient)  → floor of 2
newConcurrencyLimit = min(newConcurrencyLimit, client.maxConcurrency)
```

The floor of **2** ensures no active client ever goes to zero between cycles — it can still handle any trickle of calls arriving mid-cycle.

---

### 2.9 Execution Order Per Cycle

```
T+0s  → Data fetch: query all partner DBs for activeCalls, queuedCalls, remainingContacts
T+Xs  → Allocation runs on the fresh data just fetched
T+Xs  → Write new concurrencyLimit to every active client (partner MySQL + admin MongoDB)
T+Xs  → Log full allocation run to audit trail
T+60s → Repeat
```

---

## 3. Configuration

All settings stored in MongoDB `settings` collection. Editable via API, effective on the next cycle with no redeploy.

| Setting                    | Default              | Description                                          |
|----------------------------|----------------------|------------------------------------------------------|
| `globalMaxConcurrency`     | 200                  | Hard ceiling on total simultaneous calls             |
| `tierWeights`              | `{1:40,2:30,3:20,4:10}` | Pool % per priority tier (must sum to 100)        |
| `minConcurrencyPerClient`  | 2                    | Floor written to every active client                 |
| `allocationIntervalSeconds`| 60                   | How often the cycle runs                             |

Per-client settings on `PartnerConfig`:

| Field            | Description                                                      |
|------------------|------------------------------------------------------------------|
| `priority`       | 1–4, determines which tier pool the client draws from            |
| `maxConcurrency` | Hard ceiling for this specific client regardless of tier pool    |

---

## 4. API Endpoints

| Method | Endpoint                               | Description                                              |
|--------|----------------------------------------|----------------------------------------------------------|
| `GET`  | `/api/settings/concurrency-allocation` | Read current global config                               |
| `PUT`  | `/api/settings/concurrency-allocation` | Update config (validates tierWeights sum = 100)          |
| `POST` | `/api/concurrency/allocate-now`        | Manually trigger an allocation cycle (for testing)       |

---

## 5. Audit Trail

Every allocation cycle logs an `AllocationRun` document to MongoDB collection `allocation_runs`:

```json
{
  "runAt": "2026-03-18T10:00:00Z",
  "globalMax": 200,
  "totalInFlight": 80,
  "availableSlots": 120,
  "status": "normal",
  "allocations": [
    {
      "partnerId": "...",
      "partnerName": "Client A",
      "priority": 1,
      "tierPool": 53,
      "maxConcurrency": 50,
      "oldLimit": 40,
      "newLimit": 50,
      "remainingContacts": 10000,
      "activeCalls": 38
    }
  ]
}
```

---

## 6. Edge Cases

| Scenario                                       | Behaviour                                                          |
|------------------------------------------------|--------------------------------------------------------------------|
| System fully saturated (available ≤ 0)         | Write floor of 2 to all, skip distribution                         |
| All clients in a tier finish contacts          | Tier excluded, weight redistributed to remaining active tiers      |
| Only one client has any demand                 | Gets all available slots (capped at `maxConcurrency`)              |
| Client `maxConcurrency` < equal share          | Surplus cascades within tier first, then cross-tier                |
| `tierWeights` changed via API                  | Next cycle uses new weights immediately                            |
| `globalMaxConcurrency` reduced                 | Available shrinks, all limits scale down next cycle                |
| Client with 0 demand                           | Receives floor of 2, not excluded from write cycle                 |

---

## 7. Implementation Scope

| File                                  | Change                                                                                      |
|---------------------------------------|---------------------------------------------------------------------------------------------|
| `models.py`                           | Add `priority`, `maxConcurrency` to `PartnerConfig`; add `AllocationRun`, `ConcurrencyAllocationSettings` models |
| `services/concurrency_allocator.py`   | New file — full algorithm implementation                                                    |
| `server.py`                           | New API endpoints; wire allocator to run after data fetch in scheduler                      |

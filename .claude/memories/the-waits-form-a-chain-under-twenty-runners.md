---
name: the-waits-form-a-chain-under-twenty-runners
description: The account runs 20 jobs at once and a wait-for-* job holds a runner while it polls, so the waits chain (storage after identity, routing after both, every other stack after routing) rather than fan out; a new workflow adds one waiter
metadata:
  type: project
---

# The waits form a chain under twenty runners

GitHub runs at most 20 of this account's jobs at once, and a `wait-for-*` job is a job: it holds a runner for as long as it polls. When the waiters across all the workflows on one commit number 20 or more, the run they wait for cannot get a runner for its last job, every waiter polls until its hour is up, and nothing is applied. So the waits form a chain: `common_storage` waits for `common_identity`, `common_routing` waits for both, and every endpoint and operational workflow waits for `common_routing` alone, since routing's own waits cover what it stands on. A workflow whose foundation ended red goes red itself — the action exits 1 — so the guarantee is transitive and a failed-jobs rerun repeats the wait.

**Why:** On 2026-09-14 the eleventh workflow (`endpoint_wan_syntheses`) made 21 waiters; `0576d42`'s eight in-progress runs each polled for `common_identity`, whose reconciliation sat queued with no runner for half an hour; `7ffe1b3`'s runs had done the same behind `5c87a32`'s.

**How to apply:** A new stack's workflow gets one `wait-for-common-routing` job and nothing else; never add a `wait-for-common-identity` or `-storage` job outside `common_routing` and `common_storage`. If a run sits `queued` while others are `in_progress` for more than a few minutes, count the running `wait-for-*` jobs before anything else. Related: [[a-red-run-with-a-green-twin-on-the-same-commit-needs-no-fix]], [[a-wait-runs-in-the-background]].

---
name: a-deployed-test-writes-no-data
description: "no test may write data: a post-deployment test only reads what the deployed store already holds, and a write route is tested there only by a refusal that writes nothing; the write's logic lives in the unit tests"
metadata:
  node_type: memory
  type: feedback
  originSessionId: bf55e534-a8df-4c39-8a71-4a6fd6d11260
  modified: 2026-10-08T01:57:07.319Z
---

# A deployed test writes no data

No test may write data. A post-deployment test reads what the deployed API and its store already hold, and a route that writes is tested there only by a request it refuses before writing (a 400, 401, 403 or 404). What the write does is tested in the unit tests.

**Why:** the user filed #258–#262 on 2026-10-08, each opening "no test may write data". A write stays visible to every reader while it exists: `10U-Labs/wan-synthesizer`'s syntheses ETL e2e test went red on a synthesis labelled `post-deployment-tests` that this repository's routing test had created. A teardown never undoes all of a write either. `next_id` spends a counter value for good, a synthesis still running refuses its delete with 409, and a fixture without a `finally` leaves its row behind when the run stops.

**How to apply:** a deployed test that needs a stored member finds one by reading, for instance the first listed synthesis whose record says `success`. When nothing readable names one, it checks the deployed configuration instead, for instance that `/rack-configurations/*` sits under the carriers' cache policy. It never POSTs, PUTs or DELETEs anything the route would accept. Related: [[the-deployed-tests-hold-only-the-workflows-key]], [[a-cached-route-lets-every-method-through-and-is-read-until-it-hits]].

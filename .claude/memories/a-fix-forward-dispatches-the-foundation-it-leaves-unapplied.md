---
name: a-fix-forward-dispatches-the-foundation-it-leaves-unapplied
description: "when a red push left a foundation (routing) unapplied and the fix forward's paths do not fire it, dispatch that workflow on the fix commit right after pushing, so the dependents' wait jobs find it by head_sha"
metadata:
  node_type: memory
  type: feedback
  originSessionId: bf55e534-a8df-4c39-8a71-4a6fd6d11260
  modified: 2026-10-07T13:12:59.850Z
---

# A fix forward dispatches the foundation it leaves unapplied

A fix forward fires only the workflows its own paths name. When the red push changed a foundation such as `src/www/openapi.json` and the fix touches only one stack's tests, the foundation's workflow never runs again and its change stays unapplied, while the dependent goes on to test against what is deployed.

**Why:** 20767c5 added the carriers PUT routes to `openapi.json` and went red on lint in the deployed tests, so routing never applied. The fix, 6629b1a, touched only `test/api/endpoints/carriers/`, which fires carriers alone; its deployed tests would have hit routes API Gateway did not have yet.

**How to apply:**

- Push the fix, then at once `gh workflow run <foundation>.yml --ref main`, before the dependent's wait job polls.
- `wait-for-workflow` looks the foundation's run up by `head_sha` whatever its event, so the dependent waits for the dispatched run, and the dispatched run's own waits pass because its event is not `push`.
- See [[the-waits-form-a-chain-under-twenty-runners]] and [[a-red-run-with-a-green-twin-on-the-same-commit-needs-no-fix]].

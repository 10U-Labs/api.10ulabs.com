---
name: a-fix-forward-fires-every-stack-the-red-commit-changed
description: A fix-forward commit must touch a path that fires every workflow whose stack the red commit changed, or the skipped reconciliations never run
metadata:
  type: feedback
---

# A fix forward fires every stack the red commit changed

A red gate that every workflow runs (jscpd, pylint, an `assert-*` over `test/`) skips every reconciliation on that commit. The follow-up commit fires only the workflows whose `on.push.paths` it touches, so a fix confined to one test file leaves the other stacks un-applied and their integration tests reading a deployment that never received the red commit's change.

**Why:** On 2026-09-14 `0d2ecaa` (PUT /carriers/{carrier}) went red on `copy-paste-tests`, so `common_routing` never applied the new operation; the fix `cb33b19` touched a carriers test alone, so only `endpoint_carriers` fired and its integration test met an API Gateway without the put and got 404 through the catch-all. `68331bd`, a real change under `src/www/**`, fired everything and the carriers workflow's `wait-for-common-routing` sequenced it.

**How to apply:** Before pushing a fix forward, list the stacks the red commit changed and check the fix touches a path each of their workflows filters on (`src/www/**` and `lib/python/**` fire all of them). If the honest fix does not, find a genuine improvement under a shared path rather than a no-op edit. Related: [[a-rejected-push-is-fixed-forward]], [[ci-is-the-source-of-truth]].

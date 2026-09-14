---
name: a-grant-a-stack-needs-lands-before-the-stack
description: The wait chain sequences only the workflows that fire on the same commit, so a stack needing a new grant from identity is reconciled after the grant is applied, by pushing the grant first or re-running the stack's failed reconciliation on the same commit
metadata:
  type: feedback
---

# A grant a stack needs lands before the stack

The waits form a chain through `common_routing`, but a wait finds nothing to wait for when the workflow it waits on did not fire on the commit. A commit that touches `src/api/common/identity/**` and a stack fires identity and the stack; the stack waits for routing, routing did not fire, so the stack's reconciliation starts at once and races identity's apply.

**Why:** On 2026-09-14 `45bb9b7` granted the deploy role `lambda:PublishLayerVersion` and declared the solver layer in the wan syntheses stack in one push; the stack's reconciliation started 37 seconds before identity's apply finished and was refused the same action a second time. `gh run rerun --failed` on the stack's run, once identity was green, published the layer, and the loader and the e2e ran behind it.

**How to apply:** When a stack needs a grant the deploy role does not have, the refusal names the action and the resource; add the statement to `src/api/common/identity/iam.tf` with its test. Then either push the grant on its own commit and the stack after identity is green, or push both and re-run the stack's failed reconciliation on the same commit once identity has applied; a run that failed before its grant landed is not a red gate to fix forward. Related: [[the-waits-form-a-chain-under-twenty-runners]], [[a-red-run-with-a-green-twin-on-the-same-commit-needs-no-fix]].

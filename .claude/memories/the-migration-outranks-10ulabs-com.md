---
name: the-migration-outranks-10ulabs-com
description: "Moving the API into this repository is the only thing that matters; 10ulabs.com's workflows going red is accepted, its collateral is never fixed, and a change it needs is applied by hand when its gates are red"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 7b493447-0b21-4738-8061-11711588c598
  modified: 2026-09-13T22:42:03.375Z
---

# The migration outranks 10ulabs.com

Moving api.10ulabs.com into this repository, route by route, is the
only thing that matters. `10ulabs.com` and its apps may break along the
way, and its workflows may go and stay red; that is accepted.

**Why:** the user said so on 2026-09-13, and said it again after the
session kept spending commits there anyway: a retirement (#5) left an
unread output, two orphaned fixture builders and an unused import
behind, and each was "fixed" on the argument that the red gate sat in
front of the `reconciliation` job the next CloudFront change needed.
That argument was rejected. A red gate in `10ulabs.com` is not a reason
to touch anything in `10ulabs.com` that the issue at hand does not name.

**How to apply:**

- A `Retire ... from 10ulabs.com` issue is done when the stack is
  destroyed by hand, its state object deleted, and the directory, tests,
  workflow and OpenAPI path removed, as the issue proposes. Nothing
  else there is edited, whatever its checks say afterwards.
- A `Serve ...` issue's `10ulabs.com` half is one commit adding the
  CloudFront behaviour (or origin) the issue names, pushed once. If
  that repository's run is red for any reason but the change itself,
  apply `src/api/common/routing` there by hand with `tofu`, the way the
  retirements destroy by hand, and move on.
- Do not read a red `10ulabs.com` run for collateral to fix. Its
  lints, tests, libraries and other stacks are not on the migration's
  path.
- In this repository nothing changes: every workflow that fires is green
  before an issue is done, per
  [ci-is-the-source-of-truth](ci-is-the-source-of-truth.md).

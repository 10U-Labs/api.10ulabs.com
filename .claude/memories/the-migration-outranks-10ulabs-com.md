---
name: the-migration-outranks-10ulabs-com
description: "Moving the API into this repository is the only thing that matters; 10ulabs.com and its apps breaking along the way is accepted, so a retirement there is done minimally and its collateral is not chased"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 7b493447-0b21-4738-8061-11711588c598
  modified: 2026-09-13T21:41:25.336Z
---

# The migration outranks 10ulabs.com

Moving api.10ulabs.com into this repository, route by route, is the
only thing that matters. `10ulabs.com` and its apps may break along the
way; that is accepted, not to be prevented.

**Why:** the user said so on 2026-09-13, after the retirement of
`GET /health` from `10ulabs.com` (#3) had spent two follow-up commits
there on collateral its own gates raised — an unread module output, an
e2e test over a CORS preflight the new route never offered.

**How to apply:** a `Retire ... from 10ulabs.com` issue is done when the
stack is gone, its state object deleted, and the directory, tests,
workflow and OpenAPI path removed, as the issue proposes. Do what that
takes and no more: do not widen a retirement to keep `10ulabs.com`'s
other stacks, tests or apps working, and do not stop to repair breakage
there that is not on the migration's path. A red run in `10ulabs.com`
still gets read, since it may name a wiring the retirement missed, but a
finding about something else is left where it lies. In this repository
nothing changes: every workflow that fires is green before an issue is
done, per [ci-is-the-source-of-truth](ci-is-the-source-of-truth.md).

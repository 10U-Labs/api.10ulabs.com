---
name: the-first-parameter-of-a-path-is-id
description: "API Gateway allows one variable child per resource, so every path through a position shares one name; the first parameter of a path is {id} and a later one names its noun, {pop_id}"
metadata: 
  node_type: memory
  type: project
  originSessionId: 031b261b-64e4-41fc-a300-e61fb398bf64
  modified: 2026-09-16T10:28:14.115Z
---

# The first parameter of a path is `{id}`

The first parameter of a path is `{id}` and every parameter after it names its noun with an `_id` suffix: `/carriers/{id}`, `/carriers/{id}/pops/{pop_id}`, `/wan-syntheses/{id}/sites/{site_id}`, `/sessions/{id}/events`.

**Why:** An API Gateway REST API resource may have only one variable child — `PutRestApi` refuses a spec that has both `/carriers/{id}` and `/carriers/{carrier_id}/pops` with "A sibling ({id}) of this resource already has a variable path part -- only one is allowed". So a position in the tree carries one name for every path through it, and the "leaf is `{id}`, holder is `{holder_id}`" scheme cannot be deployed: the carrier is a leaf in `/carriers/{id}` and a holder in `/carriers/{id}/pops`, and the two are the same resource. Commit `2d45b0c` went red on this on 2026-09-16; `test_openapi.py` holds two tests that pin the rule.

**How to apply:** A new route reads its first parameter as `id` and a deeper one as `<noun>_id`, in `openapi.json`, in the handler's dispatch key and `path_id` call, and in the unit tests' `pathParameters`. Because the same resource is shared, the routing stack's apply — not the unit tests — is what catches a clash; see [[ci-is-the-source-of-truth]] and [[no-v1-in-any-api-or-url]].

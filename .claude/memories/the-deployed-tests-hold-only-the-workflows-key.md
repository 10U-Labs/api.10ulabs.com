---
name: the-deployed-tests-hold-only-the-workflows-key
description: Post-deployment tests can bear only the workflows' API key, so a route the authorizer denies that key is tested for its 403 and its logic in the unit tests
metadata:
  type: project
---

# The deployed tests hold only the workflows' key

The post-deployment integration tests authenticate with the API key from SSM (`/api.10ulabs.com/api-key`). The authorizer admits that key to `GET /*` and to `WORKFLOW_WRITES` only; a Google ID token for an authorized account cannot be minted in CI.

**Why:** Decided while serving PUT /carriers/{carrier} on 2026-09-14: the rename is a human-only write, no workflow needs it, and widening the key for a test would widen it in production.

**How to apply:** A route the key may call is exercised through the deployed API (a 404 on `/carriers/0` proves both the route and the grant). A route the key may not call gets a deployed test that the key is refused (403) and has its behaviour covered by the unit tests. A write a workflow needs is added to `WORKFLOW_WRITES` in the authorizer with its own authorizer unit test, as DELETE /carriers/* was. Related: [[the-verbs-are-the-only-way-in]], [[write-the-test-first]].

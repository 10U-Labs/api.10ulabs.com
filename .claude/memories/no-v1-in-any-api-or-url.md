---
name: no-v1-in-any-api-or-url
description: "No path segment `v1` in any API or URL this repository serves or names; a route 10ulabs.com served under /v1/ is served here without it"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 143c9f4f-ff2b-4f4e-9394-9136208a51a7
  modified: 2026-09-13T23:48:51.557Z
---

# No v1 in any API nor URL

No `v1` in any API nor URL. A route `10ulabs.com` served as `/v1/sessions/{session_id}/events` is served here as `/sessions/{session_id}/events`; the OpenAPI paths, the handler's dispatch keys, the tests, the CloudFront behaviours and the site's calls all say the path without the prefix.

**Why:** The user said so on 2026-09-13, mid-way through #12: "no v1/ -- 'v1' should not be used in any API nor URL". The API is not versioned by path; the `v1` was `10ulabs.com`'s and does not come along in the migration.

**How to apply:** When an issue's title or body names a `/v1/...` route, serve it without the `v1` and say so in the commit. Never add a path, tag, behaviour or test that carries `v1`. See [[the-migration-outranks-10ulabs-com]] for what happens to `10ulabs.com` on the way.

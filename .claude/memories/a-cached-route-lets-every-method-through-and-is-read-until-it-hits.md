---
name: a-cached-route-lets-every-method-through-and-is-read-until-it-hits
description: "a CloudFront behavior on the reads policy allows every method and caches GET and HEAD, since the writes share the reads' paths and a GET-only behavior would refuse them; a deployed test of a cache hit re-reads a bounded number of times, since the next request need not land on the node that cached the last"
metadata: 
  node_type: memory
  type: project
  originSessionId: 9e3c5421-3b58-49e5-b494-8ecfd9440ef1
  modified: 2026-09-17T07:27:49.170Z
---

# A cached route lets every method through and is read until it hits

The reads cache policy (`aws_cloudfront_cache_policy.reads` in `src/api/common/routing/cloudfront.tf`) keys on the path and the `Authorization` header alone; its behaviors are `/carriers`, `/carriers/*`, the regions pair, `/rack-configurations/*`, `/wan-syntheses` and `/wan-syntheses/*`, each with `allowed_methods` of all seven and `cached_methods` of GET and HEAD. The default behavior stays on `Managed-CachingDisabled`.

**Why:** Issue #138 asked for GET/HEAD-only behaviors, but `PUT /carriers/{id}` shares its path with the read, and CloudFront refuses a method a behavior does not allow, so writes would have stopped reaching the gateway. On 2026-09-17 `afd4937`'s deployed test asserted a hit on the very next read of `/carriers` and got `Miss from cloudfront` once; `f15a011` made the test re-read up to five more times.

**How to apply:** A new cached route gets a behavior allowing every method on the reads policy; the writes on it must invalidate what they stale first, per the `staled` helpers in each stack's shared module. A deployed test that a route is cached uses `_repeated` in `test/api/common/routing/post_deployment/integration/test_cached_reads.py`, never a single second read. Related: [[the-deployed-tests-hold-only-the-workflows-key]], [[a-red-run-with-a-green-twin-on-the-same-commit-needs-no-fix]].

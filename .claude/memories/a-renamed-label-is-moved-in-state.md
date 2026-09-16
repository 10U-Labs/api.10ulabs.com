---
name: a-renamed-label-is-moved-in-state
description: "renaming a resource's label needs a `moved` block, or tofu destroys the old and creates the new, and destroys first; a CloudFront policy or OAC in use refuses the destroy and the apply halts before the distribution switches"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f2771202-29a0-42bd-874d-c54ee80f476f
  modified: 2026-09-16T11:54:54.217Z
---

# A renamed label is moved in state

A resource whose label changes in code (`aws_cloudfront_cache_policy.docs` to `.www`) carries a `moved { from to }` block, so tofu renames it in state. Without one, tofu plans the old address destroyed and the new one created, and orders the destroy before the update of whatever referenced the old address.

**Why:** On 2026-09-16 `813530a` relabelled the routing stack's bucket, cache policy and origin access control from `docs` to `www` with no `moved` blocks. The bucket was meant to be replaced (its name changed), but the cache policy and OAC were not: tofu created new ones, then tried to delete the old two before updating the distribution off them, CloudFront refused with `CachePolicyInUse` / `OriginAccessControlInUse`, and the apply halted with the distribution still pointing at the already-destroyed bucket, so `/` answered 404 until `cde7794` moved the old two to a `retired` label and kept them for one apply and `9c6ee93` dropped them.

**How to apply:** Every label rename gets a `moved` block in the same commit. When the old resource is already orphaned in state and in use by a survivor, move it to a holding label and keep it declared for one apply, then drop it in the next commit. Related: [[a-rejected-push-is-fixed-forward]], [[ci-is-the-source-of-truth]].

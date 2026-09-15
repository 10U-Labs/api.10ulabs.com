---
name: a-by-hand-destroy-follows-the-push-that-drops-the-workflow
description: A stack destroyed by hand while its workflow still exists on the pushed history is rebuilt by any reconciliation still in flight, so destroy after the push that removes the workflow, and read the account afterwards for what a run rebuilt
metadata:
  type: feedback
---

# A by-hand destroy follows the push that drops the workflow

A stack another repository deploys is destroyed by hand with `tofu`, but a workflow run already in flight on an earlier commit does not know that: its reconciliation applies the configuration it checked out and rebuilds every resource the destroy removed, writing a fresh state object beside it.

**Why:** On 2026-09-14 `wan-synthesizer`'s providers stack was destroyed by hand for `#114` while the commit for `#113`, pushed minutes earlier, still had `api_endpoint_providers.yml` reconciling; the run rebuilt the Lambda, its role, its policies and its log group and wrote a new state object, found only when the common stacks were torn down for `#116`. The rebuilt stack could not be destroyed with `tofu` any more, its remote states being gone, and was deleted resource by resource with the AWS CLI.

**How to apply:** Push the commit that removes the stack's workflow first, then destroy the stack by hand and delete its state object; or, when the destroy must come first, list the account afterwards — functions, roles, REST APIs, state objects under the product's prefix — and delete what a run rebuilt. A runs listing is never read in that repository; the account is the only thing to check. Related: [[the-migration-outranks-10ulabs-com]], [[a-grant-a-stack-needs-lands-before-the-stack]].

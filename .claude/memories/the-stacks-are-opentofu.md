---
name: the-stacks-are-opentofu
description: "Every stack in this repository is OpenTofu, not Terraform; the shared module is lib/opentofu/common, the workflows run tofu through opentofu/setup-opentofu, and the file paths say so"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 7b493447-0b21-4738-8061-11711588c598
  modified: 2026-09-13T20:44:39.925Z
---

# The stacks are OpenTofu

Every stack under `src/` is applied with `tofu`, set up in a workflow by
`opentofu/setup-opentofu@v2`, and tagged `ManagedBy = "OpenTofu"`. The
shared module is `lib/opentofu/common`, never `lib/terraform/common`, and
any path or name that would say "terraform" says "opentofu" instead. The
two names that stay are the ones AWS and the state layout own: the bucket
`10ulabs-terraform-state-us-east-2`, the `terraform.tfstate` key, the
`.terraform/` working directory and `data "terraform_remote_state"`.

**Why:** the user said so when the first stacks were written as Terraform
after `10ulabs.com`, which still uses `hashicorp/setup-terraform`; the
sibling to copy for tooling is `wan-synthesizer`, which is OpenTofu
throughout. `10ulabs.com` remains the sibling to copy for workflow job
layout, per [an-assert-is-its-own-job](an-assert-is-its-own-job.md).

**How to apply:** `required_version = ">= 1.11"` in every `backend.tf`;
`tofu -chdir=<stack> init|validate|fmt|apply` in the workflows; the
`assert-opentofu-resource-is-used` action over each stack and
`lib/opentofu/common`. Do not add `hashicorp/setup-terraform` or a
`terraform` binary step anywhere.

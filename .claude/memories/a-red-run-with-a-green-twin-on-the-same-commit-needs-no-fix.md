---
name: a-red-run-with-a-green-twin-on-the-same-commit-needs-no-fix
description: A red run needs no fix forward when the same commit has a green run of the same workflow whose reconciliation applied, as when GitHub fires a push twice and one run trips on a transient download
metadata:
  type: feedback
---

# A red run with a green twin on the same commit needs no fix

A fix forward answers a red gate that left a stack un-applied. When a workflow ran twice on one commit and one of the runs is red for a reason outside the code — a `setup-*` action's download answering 500 — while the other is green with its `reconciliation` and `post-deployment-integration-tests` jobs successful, the stack is applied and verified on that commit and nothing is left to fix.

**Why:** On 2026-09-14 the push of `5a5c1d2` reached GitHub as two push events three seconds apart, so every workflow ran twice; `common_routing`'s first run failed in `opentofu/setup-opentofu` on a 500 from the OpenTofu release download, its second run was green through reconciliation, and `endpoint_carriers` waited on the green one and tested the deployed route. A follow-up commit would have changed nothing.

**How to apply:** When the wait prints more runs than workflows, group them by workflow before reading a failure; a red run whose twin on the same `headSha` is green through reconciliation is not a red gate. Read the red run's failed log all the same, and fix forward if it names the code. Related: [[a-rejected-push-is-fixed-forward]], [[a-fix-forward-fires-every-stack-the-red-commit-changed]], [[find-a-run-by-the-full-hash]].

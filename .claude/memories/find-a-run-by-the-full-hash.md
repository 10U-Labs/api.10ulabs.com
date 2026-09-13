---
name: find-a-run-by-the-full-hash
description: gh run list --commit returns an empty list for a short hash, so match headSha by prefix locally instead
metadata:
  type: feedback
---

# Find a run by the full hash

Find the run by the full forty-character hash, from `git rev-parse HEAD`. `gh run list --commit` silently returns an empty list for the short hash `git log --oneline` prints, which is indistinguishable from a run that has not started, so anything that polls should instead run `gh run list --limit 10 --json workflowName,status,conclusion,headSha` and match `headSha` by prefix locally.

Why the run is read at all is [ci-is-the-source-of-truth](ci-is-the-source-of-truth.md).

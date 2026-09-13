---
name: a-rejected-push-is-fixed-forward
description: A push rejected by CI is answered with a follow-up commit, never an amend and force-push
metadata:
  type: feedback
---

# A rejected push is fixed forward

A push rejected by CI is answered with a follow-up commit. Do not amend and force-push: `main` is published by the time the run reports, and rewriting it discards what was tried. Where this collides with solving an issue in a single push, verifying only in CI is the rule that holds and the extra commits are its cost — local linting has been proposed and declined.

Read the whole failed log rather than its first error, and sweep the change for other instances of the same shape before pushing the fix. A run reports every gate at once, so a fix that answers only the first line of the log buys one more red run.

The rule it defers to is [ci-is-the-source-of-truth](ci-is-the-source-of-truth.md); what makes `main` already published is [commit-straight-to-main](commit-straight-to-main.md).

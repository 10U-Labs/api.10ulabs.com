---
name: commit-straight-to-main
description: Work goes straight to main as direct commits; no feature branches, no pull requests, no review cycle
metadata:
  type: feedback
---

# Commit straight to main

Work goes straight to `main` as direct commits. Do not create a feature branch, do not open a pull request, and do not structure advice around a review cycle.

There is no pull-request buffer, so CI is the only review there is, and the tests land in the same commit as the code they cover rather than in a follow-up somebody has to remember. A rejected push is answered forward from the same branch: [a-rejected-push-is-fixed-forward](a-rejected-push-is-fixed-forward.md).

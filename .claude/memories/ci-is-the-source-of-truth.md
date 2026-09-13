---
name: ci-is-the-source-of-truth
description: Do not run tests, linters or builds locally to verify a change: commit, push to main, and read the run
metadata:
  type: feedback
---

# CI is the source of truth

Do not run tests, linters or builds locally to verify a change — write the code and the tests, commit, push to `main`, and read the run with `gh run list` / `gh run watch` / `gh run view --log-failed`. Local runs cost tokens; CI is free and checks every gate at once.

A push can trigger several path-filtered workflows. The change is done when each workflow that fired is green, not when the first one is.

What to do with a red run is [a-rejected-push-is-fixed-forward](a-rejected-push-is-fixed-forward.md); where the push goes is [commit-straight-to-main](commit-straight-to-main.md).

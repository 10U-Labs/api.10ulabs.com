---
name: one-gitignore-at-the-root
description: The repository has exactly one .gitignore, at its root; no directory carries its own
metadata:
  type: feedback
---

# One .gitignore, at the root

There is one `.gitignore` in the whole repository, the one at its root. A pattern a stack or a directory needs is added there, never in a `.gitignore` beside the files it covers.

**Why:** The user's rule, given on 2026-09-13 when nine OpenTofu stacks each carried an identical four-line `.gitignore`: "there should be only one .gitignore in the entire repo; the one at the repo's root." One file says everything that is ignored; nine copies say the same thing and drift.

**How to apply:** Before adding a `.gitignore` anywhere under `src/`, `test/` or `lib/`, add the pattern to the root file instead. When copying a layout from `10ulabs.com` (see [[an-assert-is-its-own-job]]), leave its per-directory `.gitignore` files behind. Related: [[the-stacks-are-opentofu]].

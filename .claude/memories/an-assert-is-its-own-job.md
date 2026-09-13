---
name: an-assert-is-its-own-job
description: Each assert-* check is a standalone workflow job using the tool's published 10U-Labs action, not a step inside the linter job it guards
metadata:
  type: feedback
---

# An assert is its own job

Each `assert-*` check in a workflow is a job of its own, named after the tool (`assert-no-inline-directives`, `assert-no-linter-config-files`), and runs the tool's published action from the `10U-Labs` org at `@latest` rather than pip-installing the package. A linter job (`markdownlint`, `yamllint`) holds only its lint step; the asserts that guard it list the linter in their `tools` or `linters` input. This is the shape used in `10ulabs.com`, and it differs from `wan-synthesizer`, where the asserts are steps inside the linter job — the sibling repo to copy for job layout is `10ulabs.com`.

A separate job reports as a separate check, so a red run says which rule was broken without reading a log, and the asserts run in parallel with the lint instead of gating it. Actions are preferred over installing packages in a `run:` step generally; the exception is a tool whose action cannot take the flags the job needs, such as `markdownlint-cli` and `--disable MD013`.

What the asserts protect is the CI-only verification in [ci-is-the-source-of-truth](ci-is-the-source-of-truth.md).

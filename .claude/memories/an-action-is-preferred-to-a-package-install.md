---
name: an-action-is-preferred-to-a-package-install
description: A workflow step uses a published GitHub action rather than installing the tool with pip or npm in a run step
metadata:
  type: feedback
---

# An action is preferred to a package install

A workflow step uses a published GitHub action for its tool rather than installing the package with `pip install` or `npm install` in a `run:` step. The `assert-*` tools have actions in the `10U-Labs` org, used at `@latest`; yamllint has `ibiqlik/action-yamllint`, which takes its rules inline as `config_data`. Look for an action before writing an install line, and check the tool's own repository first — the 10U-Labs tools publish theirs alongside the package.

An action states what the step does in one `uses:` line and carries its own install, so the workflow reads as a list of tools rather than a script. The exception is a tool whose action cannot take the flags the job needs: `markdownlint-cli` is installed with npm because `--disable MD013` has no action input, and passing it through a config file would break `assert-no-linter-config-files`.

How the assert actions are laid out as jobs is [an-assert-is-its-own-job](an-assert-is-its-own-job.md).

# Notes for Claude sessions in api.10ulabs.com

## Table of Contents

- [Overview](#overview)
- [Conventions](#conventions)
  - [Commits](#commits)
  - [Tests](#tests)
  - [Verification](#verification)
  - [Workflows](#workflows)
  - [Cost](#cost)
  - [Writes](#writes)
  - [Stacks](#stacks)
  - [Priority](#priority)

## Overview

This directory is the rulebook. One memory holds one rule, so a session can recall the one it needs without reading the rest, and each file carries the reasoning behind its rule rather than only the instruction. This index is read at the start of every session and the memories themselves are recalled by relevance, so each line below says enough to know whether the file behind it is the one to open. A convention learned in a session belongs here, as a new memory and a line in this index.

## Conventions

### Commits

- [commit-straight-to-main](commit-straight-to-main.md) — direct commits to `main`, no feature branch and no pull request
- [a-rejected-push-is-fixed-forward](a-rejected-push-is-fixed-forward.md) — a red run is answered with a follow-up commit, never an amend and force-push
- [an-issue-is-closed-by-its-commit](an-issue-is-closed-by-its-commit.md) — a `Closes #N` line in the commit that solves it, one line per issue; naming an issue in prose references it without closing it

### Tests

- [write-the-test-first](write-the-test-first.md) — the test is authored before the code, and red and green are observed in CI

### Verification

- [ci-is-the-source-of-truth](ci-is-the-source-of-truth.md) — nothing is verified locally; the change is done when every workflow that fired is green
- [find-a-run-by-the-full-hash](find-a-run-by-the-full-hash.md) — `gh run list --commit` returns nothing for a short hash, so match `headSha` by prefix locally

### Workflows

- [an-action-is-preferred-to-a-package-install](an-action-is-preferred-to-a-package-install.md) — a step uses the tool's published action, not `pip install` or `npm install` in a `run:` step; the exception is a tool whose action cannot take the needed flags
- [an-assert-is-its-own-job](an-assert-is-its-own-job.md) — each `assert-*` check is a standalone job using its published `10U-Labs` action; linter jobs hold only the lint step; copy `10ulabs.com` for layout

### Cost

- [the-cheapest-backend-wins](the-cheapest-backend-wins.md) — a backend is chosen by its monthly cost alone, to the fraction of a cent; provisioned DynamoDB inside the always-free tier costs nothing, S3 never does

### Writes

- [the-verbs-are-the-only-way-in](the-verbs-are-the-only-way-in.md) — no seed and no loader; a collection's workflow calls its HTTP verbs on a push to the data it serves, for what changed only

### Stacks

- [the-stacks-are-opentofu](the-stacks-are-opentofu.md) — every stack is OpenTofu, set up by `opentofu/setup-opentofu` and run as `tofu`; the shared module is `lib/opentofu/common`, and no path says `terraform` but the state bucket and key

### Priority

- [the-migration-outranks-10ulabs-com](the-migration-outranks-10ulabs-com.md) — moving the API here is all that matters; `10ulabs.com` may go and stay red, its collateral is never fixed, and a CloudFront change it needs is applied by hand when its gates are red

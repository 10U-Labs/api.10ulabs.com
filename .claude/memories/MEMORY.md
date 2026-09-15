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
  - [Paths](#paths)
  - [Layout](#layout)
  - [Issues](#issues)

## Overview

This directory is the rulebook. One memory holds one rule, so a session can recall the one it needs without reading the rest, and each file carries the reasoning behind its rule rather than only the instruction. This index is read at the start of every session and the memories themselves are recalled by relevance, so each line below says enough to know whether the file behind it is the one to open. A convention learned in a session belongs here, as a new memory and a line in this index.

## Conventions

### Commits

- [commit-straight-to-main](commit-straight-to-main.md) — direct commits to `main`, no feature branch and no pull request
- [a-rejected-push-is-fixed-forward](a-rejected-push-is-fixed-forward.md) — a red run is answered with a follow-up commit, never an amend and force-push
- [an-issue-is-closed-by-its-commit](an-issue-is-closed-by-its-commit.md) — a `Closes #N` line in the commit that solves it, one line per issue; naming an issue in prose references it without closing it

### Tests

- [write-the-test-first](write-the-test-first.md) — the test is authored before the code, and red and green are observed in CI
- [the-deployed-tests-hold-only-the-workflows-key](the-deployed-tests-hold-only-the-workflows-key.md) — post-deployment tests bear only the workflows' API key; a route it is denied is tested for its 403, its logic in the unit tests
- [a-fixture-consumed-in-its-own-file-is-named](a-fixture-consumed-in-its-own-file-is-named.md) — `name=` on a `*_fixture` function when the file that defines a fixture also requests it, a plain `def` when only other files do; W0621 and `assert-pytest-fixture-name-is-needed` pull opposite ways

### Verification

- [ci-is-the-source-of-truth](ci-is-the-source-of-truth.md) — nothing is verified locally; the change is done when every workflow that fired is green
- [find-a-run-by-the-full-hash](find-a-run-by-the-full-hash.md) — `gh run list --commit` returns nothing for a short hash, so match `headSha` by prefix locally
- [a-wait-runs-in-the-background](a-wait-runs-in-the-background.md) — a wait for CI is a background shell or a Monitor, never a foreground sleep or `gh run watch`, so the reminders keep firing
- [a-fix-forward-fires-every-stack-the-red-commit-changed](a-fix-forward-fires-every-stack-the-red-commit-changed.md) — a fix forward touches a path that fires every workflow whose stack the red commit changed, or their skipped reconciliations never run
- [a-red-run-with-a-green-twin-on-the-same-commit-needs-no-fix](a-red-run-with-a-green-twin-on-the-same-commit-needs-no-fix.md) — a red run whose twin on the same commit is green through reconciliation is not a red gate, and a job that tripped on a transient registry or download error is re-run on the same commit — in full, foundations first, when a foundation went red, since the dependents' wait jobs keep `apply=false`; group runs by workflow when a push fired twice
- [a-failed-lambda-update-leaves-the-state-ahead-of-the-function](a-failed-lambda-update-leaves-the-state-ahead-of-the-function.md) — a reconciliation refused on a Lambda's configuration keeps the planned `source_code_hash` without uploading the code, so the fix forward must change the zip and the log must show the hash moving; a description is 256 characters at most

### Workflows

- [an-action-is-preferred-to-a-package-install](an-action-is-preferred-to-a-package-install.md) — a step uses the tool's published action, not `pip install` or `npm install` in a `run:` step; the exception is a tool whose action cannot take the needed flags
- [an-assert-is-its-own-job](an-assert-is-its-own-job.md) — each `assert-*` check is a standalone job using its published `10U-Labs` action; linter jobs hold only the lint step; copy `10ulabs.com` for layout
- [the-waits-form-a-chain-under-twenty-runners](the-waits-form-a-chain-under-twenty-runners.md) — 20 concurrent jobs, a polling wait holds one, so storage waits for identity, routing for both, everything else for routing alone; a new workflow adds one waiter
- [a-grant-a-stack-needs-lands-before-the-stack](a-grant-a-stack-needs-lands-before-the-stack.md) — the chain sequences only workflows that fire on the same commit; a stack needing a new grant from identity is reconciled after the grant applied, by pushing the grant first or re-running the failed reconciliation on the same commit

### Cost

- [the-cheapest-backend-wins](the-cheapest-backend-wins.md) — a backend is chosen by its monthly cost alone, to the fraction of a cent; provisioned DynamoDB inside the always-free tier costs nothing, S3 never does

### Writes

- [the-verbs-are-the-only-way-in](the-verbs-are-the-only-way-in.md) — no seed and no loader; a collection's workflow calls its HTTP verbs on a push to the data it serves, for what changed only

### Stacks

- [the-stacks-are-opentofu](the-stacks-are-opentofu.md) — every stack is OpenTofu, set up by `opentofu/setup-opentofu` and run as `tofu`; the shared module is `lib/opentofu/common`, and no path says `terraform` but the state bucket and key
- [a-by-hand-destroy-follows-the-push-that-drops-the-workflow](a-by-hand-destroy-follows-the-push-that-drops-the-workflow.md) — a run in flight on an earlier commit rebuilds a stack destroyed by hand, so destroy after the push that removes its workflow, or read the account afterwards for what a run rebuilt

### Priority

- [the-migration-outranks-10ulabs-com](the-migration-outranks-10ulabs-com.md) — moving the API here is all that matters; `10ulabs.com`'s runs are never read, not even to confirm a push, its collateral is never fixed, and a change it needs is applied by hand

### Paths

- [no-v1-in-any-api-or-url](no-v1-in-any-api-or-url.md) — no `v1` in any API nor URL; a route `10ulabs.com` served under `/v1/` is served here without it

### Layout

- [one-gitignore-at-the-root](one-gitignore-at-the-root.md) — exactly one `.gitignore`, at the root; a stack never carries its own
- [src-www-is-the-one-host](src-www-is-the-one-host.md) — `src/www` is `api.10ulabs.com` itself, so `openapi.json` sits directly there, with no `src/www/api`

### Issues

- [issues-have-no-house-style](issues-have-no-house-style.md) — no conventions on how an issue is written; a shape the existing issues share is not a rule, and a new issue is written however suits it

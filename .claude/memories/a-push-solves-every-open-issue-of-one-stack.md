---
name: a-push-solves-every-open-issue-of-one-stack
description: "A batch is every open issue whose fix lands in one stack under src/api/, bounded by the stack and never by a count; its tests go in one push and its code in the next; a change under a path every workflow fires on goes alone"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 73dd07bd-1399-4368-8016-9752267e75de
  modified: 2026-10-05T03:50:47.494Z
---

# A push solves every open issue of one stack

A batch is every open issue that shares one matter, and the matter bounds it, never a count. Two issues share a matter when their fixes land in the same stack: one directory under `src/api/` — `common/identity`, `endpoints/carriers`, `operational/health` and the rest — with its tests in the matching directory under `test/api/` and the one workflow under `.github/workflows/` that fires on both.

**Why:**

- **Waiting.** Each push waits out the chain of runs, identity before storage before routing before every endpoint ([[the-waits-form-a-chain-under-twenty-runners]]), and nothing else happens while it runs. With one issue per push, every issue pays that wait. A batch of n issues shares it n ways.
- **Shared reading.** Issues of one stack are fixed in the same handler, the same tofu and the same tests, so the reading done for the first serves the rest.
- **Visible interactions.** When two fixes interact, the interaction lies in code already open, not in a run.
- **Traceable red runs.** A red run is traced through the workflow that went red, and a stack has exactly one. Within one stack a failing job points at files the batch touched, however many issues it holds. A batch spanning stacks turns every failing job into a search through unrelated changes. What makes a batch too big to trace is the number of stacks it mixes, not the number of issues it holds, so a count would cap the wrong thing.

**How to apply:**

1. **Seed.** Take the issue the loop's command names first.
2. **Gather.** Add every open issue of the seed's stack. Leave out every issue labelled `needs decision`, and bring each issue up to date before starting it. When an issue's stack cannot be told without investigating it, take it in; if its fix turns out to land elsewhere, it leaves the batch and seeds a later one.
3. **Test.** Write the tests for every issue of the batch and push them as one commit, per [[write-the-test-first]], so CI shows them red.
4. **Solve.** Solve the issues one after another in the working tree and commit nothing until the last is done. As each one is finished, write its paragraph of the commit message into the scratchpad, so nothing depends on the context outlasting the batch. An issue that turns out to need a person's decision is labelled for one; its edits come out of the tree, and its tests come out in the commit that solves the rest, so that run can go green.
5. **Commit.** Commit once. The subject names the stack and what the batch does to it rather than joining every issue's subject; the body gives each issue its own paragraph; the message ends with one `Closes #N` line per issue ([[an-issue-is-closed-by-its-commit]]).
6. **Push and read the run.** When it goes red, trace each failing job to the issue whose change it names and fix forward ([[a-rejected-push-is-fixed-forward]]).

Some changes go in a push of their own and are never batched:

- A change under a path many workflows fire on: `lib/python/`, `lib/opentofu/common/`, `src/www/`, `test/conftest.py`, `test/api/conftest.py`, `.github/actions/` or `.github/workflows/`. Such a change alters what verifies every stack or what every stack runs through, so its fallout would hide the batch's own results.
- The fix for a red run.

A change under `.claude/`, such as a memory or a skill, can join any batch, since only the Markdown lint checks it.

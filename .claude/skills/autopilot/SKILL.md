---
name: autopilot
description: Start or stop the standing reminders that keep an autonomous issue-solving session on the rails. Use when the user says "start autopilot", "go autonomous on the open issues", "stop autopilot", or asks to clear the reminders. Takes "start" or "stop"; "start" also takes `--skip-label <label>`, repeatable, naming a label whose issues the session leaves alone.
---

# Autopilot

Four recurring reminders, one per standing rule, that fire back into this session while it works through open issues on its own. Each rule gets its own reminder so that no rule can be quietly dropped from a merged block of text, and the fire times are staggered across the ten-minute period so they arrive one at a time.

The argument is the sub-command: `start` or `stop`. `start` may be followed by `--skip-label <label>`, once per label, naming an issue label the session must not work on — `start --skip-label "needs decision"` leaves every issue carrying `needs decision` to a human. A label with a space in it is quoted.

`CronCreate`, `CronList` and `CronDelete` are deferred tools: a call made before the schema is fetched fails with `InputValidationError` and creates nothing. Fetch them first with `ToolSearch`, query `select:CronCreate,CronList,CronDelete`.

## Start

Create four jobs with `CronCreate`, exactly as listed below. Use `recurring: true` (the default), and take all four prompts verbatim, except that when `--skip-label` was given the first prompt ends with one extra sentence per label, after a space: `Skip every issue labelled "<label>".`

| Offset | Cron | Prompt |
| --- | --- | --- |
| :01 | `1,11,21,31,41,51 * * * *` | `REMINDER: Continue to solve the open issues autonomously, unless you need human feedback about ANYTHING — not just about the next open issue.` |
| :03 | `3,13,23,33,43,53 * * * *` | `REMINDER: Issues must be solved through a single commit & push.` |
| :07 | `7,17,27,37,47,57 * * * *` | `REMINDER: Do not do anything but wait while a workflow is running.` |
| :09 | `9,19,29,39,49,59 * * * *` | `REMINDER: When you come up against a problem, solve it. Do not file a GitHub issue about it and move on — a problem you met is a problem you fix, in the same session, under the same standing rules as the issue you were working on.` |

Then tell the user that four reminders are running, and the two limits that come with them: the jobs live in this session only and are gone when it ends, and recurring jobs auto-expire after seven days.

Then start working, in the same turn that created the jobs. Every open issue in the repository the session is running in is in scope, and so is any issue reached by following a `blocked_by` edge out of that set, whatever repository it lives in. Read the open issues with `gh issue list`, then read `gh api repos/{owner}/{repo}/issues/{number}/dependencies/blocked_by` for each of them and for each issue those entries reach, until nothing new comes back. Drop from consideration every issue carrying a label named by `--skip-label`; it still blocks whatever depends on it, so an issue behind it stays out of reach too. Take the lowest-numbered remaining issue in the set that no open issue blocks, preferring the repository the session is running in when two are equally unblocked, and solve it — committing in whichever repository its `Proposed Solution` names, and reading that repository's CI to confirm it. When nothing remains, every open issue being skipped or blocked, say which label or issue holds each one back and stop rather than starting on one anyway.

`.claude/memories/` in this repository is the rulebook wherever the session is working, including in another repository the traversal reaches.

## Stop

Call `CronList`, then call `CronDelete` once per job it returns — all of them, not only the four this skill created. Call `CronList` again afterwards to confirm it is empty, and report how many jobs were deleted. `CronList` returning nothing is not a failure; say the schedule was already empty and stop.

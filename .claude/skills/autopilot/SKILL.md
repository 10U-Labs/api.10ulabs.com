---
name: autopilot
description: Start, restart or stop the standing reminders, with or without the loop that works through this repository's open issues. Use when the user says "start autopilot", "go autonomous on the open issues", "go autonomous on the <label> issues", "reminders on", "reminders only", "stop autopilot", "reminders off", or asks to clear the reminders or to switch from one form to another ("restart autopilot", "switch to reminders only"). Takes "start", "start bylabel <label>", "start reminders-only", the same three forms after "restart", or "stop"; every "start" or "restart" form but "reminders-only" also takes `--skip-label <label>`, repeatable, naming a label whose issues the session leaves alone.
---

# Autopilot

Recurring reminders, one per standing rule, that fire back into this session while it works. Each rule gets its own reminder so that no rule can be quietly dropped from a merged block of text, and the fire times are staggered across the fifteen-minute period so they arrive one at a time.

`CronCreate`, `CronList`, `CronDelete`, `TaskCreate` and `TaskUpdate` are deferred tools: a call made before the schema is fetched fails with `InputValidationError` and creates nothing. Fetch them first with `ToolSearch`, query `select:CronCreate,CronList,CronDelete,TaskCreate,TaskUpdate`.

## The eight standing reminders

Every `start` form creates these.

| Cron | Prompt |
| --- | --- |
| `0,15,30,45 * * * *` | `REMINDER: Work through a set of indivisible tasks, written down with TaskCreate before the work starts and marked with TaskUpdate as each one starts and finishes.` |
| `2,17,32,47 * * * *` | `REMINDER: Nothing that happens in any repository but the one this session runs in matters. Another repository's workflows are not read, its runs are not waited for and its red gates are not looked at, not even to confirm a commit pushed there: the push is the end of the session's involvement, and a change that repository needs applied is applied by hand.` |
| `3,18,33,48 * * * *` | `REMINDER: Let every push carry exactly one commit, and let that commit hold a whole body of work: a matter solved end to end or carried out in full, or a batch of every open issue of one matter (one stack under src/api/, its tests under test/api/), bounded by the matter and never by a count.` |
| `6,21,36,51 * * * *` | `REMINDER: Keep the task list itself current, not only the marks on it: a task that arises is added the moment it does, a task that turns out unneeded is removed, and a task whose shape changed is rewritten, so that the list always says what is left to do.` |
| `7,22,37,52 * * * *` | `REMINDER: While any CI run for a commit pushed to this repository is in progress, only wait: no diagnosis, edits or commits.` |
| `8,23,38,53 * * * *` | `REMINDER: File what you find as issues, each documenting one indivisible problem. Solve one now only if the work in hand cannot move forward without it; otherwise move on.` |
| `9,24,39,54 * * * *` | `REMINDER: Ensure every task on the list is indivisible, whether it was written with TaskCreate or rewritten with TaskUpdate: read each subject as written and count the actions it names; a subject naming more than one action is divisible, whatever single purpose those actions serve, and is split into one task per action.` |
| `10,25,40,55 * * * *` | `REMINDER: Prune completed tasks off the Claude Code structured task list: set every task marked completed to the status deleted with TaskUpdate, so that the list holds only the tasks still open.` |

## The four loop reminders

Every `start` form but `reminders-only` adds these.

On `1,16,31,46 * * * *`, by form:

`start`:

```text
REMINDER: Run gh issue list --state open --search '-label:"needs decision"' --limit 1000 --json number,title,labels --jq 'sort_by(.number) | map({number, title, labels: [.labels[].name]})' for the open issues no decision holds back, lowest number first; take the first, together with every other issue in the list of its matter (fixed in the same stack under src/api/, its tests under test/api/), as one batch, and run the same command again when they close. An issue labelled 'needs decision' is left to a person.
```

`start bylabel <label>`:

```text
REMINDER: Run gh issue list --state open --label '{L}' --search '-label:"needs decision"' --limit 1000 --json number,title,labels --jq 'sort_by(.number) | map({number, title, labels: [.labels[].name]})' for the open issues labelled '{L}', lowest number first; take the first, together with every other issue in the list of its matter (fixed in the same stack under src/api/, its tests under test/api/), as one batch, and run the same command again when they close. The open issues without the label '{L}' are not this loop's work, and an issue labelled 'needs decision' is left to a person.
```

And these:

| Cron | Prompt |
| --- | --- |
| `4,19,34,49 * * * *` | `REMINDER: Continue autonomously, unless you need human feedback about ANYTHING — not just about what to take next. When you do, rewrite the issue's title if necessary, rewrite the issue's body, label the issue 'needs decision', and move on to the next issue.` |
| `5,20,35,50 * * * *` | `REMINDER: Before working on an issue, ensure the issue is up to date. If it is outdated, rewrite its title and body as necessary and ensure its labels are correct. Ensure too that it documents a single indivisible problem; if it documents more than one, split it into one issue per problem, reusing the issue itself as one of those splits.` |
| `11,26,41,56 * * * *` | `REMINDER: Before labeling an issue with 'needs decision', assess the issue against the rulebook in .claude/memories/ and the code to determine whether it truly needs a decision.` |

## Start

Any form but `reminders-only` may be followed by `--skip-label <label>`, once per label, quoted when it holds a space. Each adds a `-label:"<label>"` term to the loop command's `--search` flag, after the `needs decision` term — `--search '-label:"needs decision" -label:"blocked"'` — and appends to that reminder, after a space, `An issue labelled '<label>' is left to a person, whatever else it carries.`

For any form but `reminders-only`, run the loop's `gh issue list` command once; if it names no issue, create the eight standing reminders only.

Call `CronList`. A job on one of the form's cron slots whose prompt differs from that slot's reminder is a stale version of it: `CronDelete` it. Then `CronCreate` with `recurring: true` each reminder of the form whose prompt is not already scheduled, substituting the label for `{L}`.

Then tell the user how many reminders are running, and the two limits that come with them: the jobs live in this session only and are gone when it ends, and recurring jobs auto-expire after seven days.

Then, for any form but `reminders-only`, begin solving the batch the command's first issue seeds, in the same turn that created the jobs.

## Restart

`restart` takes the forms `start` takes, with the same `--skip-label` flags, and leaves scheduled exactly the reminders of the form it names, whatever was scheduled before.

For any form but `reminders-only`, run the loop's `gh issue list` command once; if it names no issue, the form's reminders are the eight standing reminders only.

Call `CronList`. `CronDelete` every job that is not one of the form's reminders: a job on a slot the form does not use, a job whose prompt differs from its slot's reminder, and every job but one on a slot that holds more than one. Then `CronCreate` with `recurring: true` each reminder of the form whose prompt is not scheduled after those deletions, substituting the label for `{L}`. Then, for any form but `reminders-only`, begin solving the batch the command's first issue seeds.

## Batches

A loop takes a batch, not a single issue: the issue its command names first, with every open issue it lists of the same matter, meaning fixed in the same stack under `src/api/`. Only this repository's open issues are in scope. `.claude/memories/a-push-solves-every-open-issue-of-one-stack.md` gives the rule in full: why the stack bounds the batch rather than a count, how the batch's tests and code go in two pushes, and which changes go in a push of their own.

When the command names no issue, say which label holds back each open issue that remains, and stop working; the reminders keep running until `stop`.

`.claude/memories/` is the rulebook.

## Stop

Call `CronList`, then call `CronDelete` once per job it returns — all of them, not only the ones this skill created. Call `CronList` again afterwards to confirm it is empty, and report how many jobs were deleted. `CronList` returning nothing is not a failure; say the schedule was already empty and stop.

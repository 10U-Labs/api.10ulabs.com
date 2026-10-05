---
name: autopilot
description: Start, restart or stop the autopilot reminders. Use when the user says "start autopilot", "restart autopilot", "stop autopilot" or "reminders only". Takes "start", "start bylabel <label>", "start reminders-only", the same three after "restart", or "stop"; every form but "reminders-only" and "stop" also takes `--skip-label <label>`, repeatable.
---

# Autopilot

Fetch `CronCreate`, `CronList`, `CronDelete`, `TaskCreate` and `TaskUpdate` with `ToolSearch` first.

## Standing reminders

Every form.

| Cron | Prompt |
| --- | --- |
| `0,15,30,45 * * * *` | `REMINDER: Work through a set of indivisible tasks, written down with TaskCreate before the work starts and marked with TaskUpdate as each one starts and finishes.` |
| `2,17,32,47 * * * *` | `REMINDER: Nothing that happens in any repository but the one this session runs in matters. Another repository's workflows are not read, its runs are not waited for and its red gates are not looked at, not even to confirm a commit pushed there: the push is the end of the session's involvement, and a change that repository needs applied is applied by hand.` |
| `3,18,33,48 * * * *` | `REMINDER: Let every push carry exactly one commit, and let that commit hold a whole body of work: a matter solved end to end or carried out in full, or a batch of every open issue of one matter (one stack under src/api/, its tests under test/api/), bounded by the matter and never by a count.` |
| `5,20,35,50 * * * *` | `REMINDER: Before working on an issue, ensure the issue is up to date. If it is outdated, rewrite its title and body as necessary and ensure its labels are correct. Ensure too that it documents a single indivisible problem; if it documents more than one, split it into one issue per problem, reusing the issue itself as one of those splits.` |
| `6,21,36,51 * * * *` | `REMINDER: Keep the task list itself current, not only the marks on it: a task that arises is added the moment it does, a task that turns out unneeded is removed, and a task whose shape changed is rewritten, so that the list always says what is left to do.` |
| `7,22,37,52 * * * *` | `REMINDER: While any CI run for a commit pushed to this repository is in progress, only wait: no diagnosis, edits or commits.` |
| `8,23,38,53 * * * *` | `REMINDER: File what you find as issues, each documenting one indivisible problem. Solve one now only if the work in hand cannot move forward without it; otherwise move on.` |
| `9,24,39,54 * * * *` | `REMINDER: Ensure every task on the list is indivisible, whether it was written with TaskCreate or rewritten with TaskUpdate: read each subject as written and count the actions it names; a subject naming more than one action is divisible, whatever single purpose those actions serve, and is split into one task per action.` |
| `10,25,40,55 * * * *` | `REMINDER: Prune completed tasks off the Claude Code structured task list: set every task marked completed to the status deleted with TaskUpdate, so that the list holds only the tasks still open.` |

## Loop reminders

Every form but `reminders-only`.

On `1,16,31,46 * * * *`, for `start`:

```text
REMINDER: Run gh issue list --state open --search '-label:"needs decision"' --limit 1000 --json number,title,labels --jq 'sort_by(.number) | map({number, title, labels: [.labels[].name]})' for the open issues no decision holds back, lowest number first; take the first, together with every other issue in the list of its matter (fixed in the same stack under src/api/, its tests under test/api/), as one batch, and run the same command again when they close. An issue labelled 'needs decision' is left to a person.
```

For `start bylabel <label>`:

```text
REMINDER: Run gh issue list --state open --label '{L}' --search '-label:"needs decision"' --limit 1000 --json number,title,labels --jq 'sort_by(.number) | map({number, title, labels: [.labels[].name]})' for the open issues labelled '{L}', lowest number first; take the first, together with every other issue in the list of its matter (fixed in the same stack under src/api/, its tests under test/api/), as one batch, and run the same command again when they close. The open issues without the label '{L}' are not this loop's work, and an issue labelled 'needs decision' is left to a person.
```

| Cron | Prompt |
| --- | --- |
| `4,19,34,49 * * * *` | `REMINDER: Continue autonomously, unless you need human feedback about ANYTHING — not just about what to take next. When you do, rewrite the issue's title if necessary, rewrite the issue's body, label the issue 'needs decision', and move on to the next issue.` |
| `11,26,41,56 * * * *` | `REMINDER: Before labeling an issue with 'needs decision', assess the issue against the rulebook in .claude/memories/ and the code to determine whether it truly needs a decision.` |

## Start and restart

Each `--skip-label <label>` adds `-label:"<label>"` to the loop command's `--search` and appends `An issue labelled '<label>' is left to a person, whatever else it carries.` to its reminder.

1. Unless `reminders-only`, run the loop command once; if it names no issue, schedule the standing reminders only.
2. Call `CronList`. On `start`, `CronDelete` each job on one of the form's slots whose prompt differs from that slot's. On `restart`, `CronDelete` every job that is not one of the form's reminders, keeping one per slot.
3. `CronCreate` with `recurring: true` each of the form's reminders not already scheduled, the label substituted for `{L}`.
4. Unless `reminders-only`, solve the batch the command's first issue seeds, per `.claude/memories/a-push-solves-every-open-issue-of-one-stack.md`. When the command names no issue, say which label holds back each open issue and stop.

## Stop

`CronDelete` every job `CronList` returns.

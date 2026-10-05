---
name: long-running-commands-in-the-background
description: "Run any command that can take more than about a minute with `run_in_background: true` and end the turn, so scheduled reminders can fire while it runs"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 1ac23030-eca4-4753-b8c4-83dab1ca8fda
  modified: 2026-10-05T05:37:27.968Z
---

# Long-running commands in the background

Run every command that can take more than about a minute as a background Bash call (`run_in_background: true`), then end the turn and let its completion notification resume the work. This covers a sweep of `gh` or `aws` calls over many issues, log groups or runs, and a long `grep` or `find` over the tree, as well as the CI wait in [[a-wait-runs-in-the-background]]. Tests, lints and `tofu` runs are not among them; per [[ci-is-the-source-of-truth]], they are not run locally at all.

**Why:** the user asked on 2026-10-05 to adopt this rule from the `deltahdl` repository. The autopilot's reminders are cron jobs, and a cron job fires only while the session is idle between turns. A foreground command holds the turn for as long as it runs, so every reminder due in that time waits behind it, and the user cannot type either. A background command frees the turn as soon as it starts.

**How to apply:**

- Give a command that might not end a time limit as well, such as `perl -e 'alarm 60; exec @ARGV' <command>`; macOS has no `timeout` command.
- Send the output to a file under the scratchpad, and read that file once the notification arrives.
- Never follow a background command with a foreground wait: no `sleep`, no `until` loop, and no rereading of its output file until it fills. Any of these blocks the session again.
- If other work does not depend on the result, it may go on in the meantime, except while a CI run is in progress, when idle means idle. Once only the result is left to wait for, end the turn.
- A turn made of many short foreground calls also holds the reminders back until it ends. Split long work at its natural boundaries, such as after a batch of issues is filed or after a batch of edits, rather than running it all in one turn.

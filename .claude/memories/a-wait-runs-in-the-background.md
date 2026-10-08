---
name: a-wait-runs-in-the-background
description: "A wait for CI or anything else is a Bash run_in_background or a Monitor, never a foreground sleep or gh run watch, so the session stays idle and the autopilot reminders can fire"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 143c9f4f-ff2b-4f4e-9394-9136208a51a7
  modified: 2026-10-08T01:22:12.748Z
---

# A wait runs in the background

Waiting for a workflow run, a dispatch, an invalidation or anything else that takes minutes is done with `Bash` and `run_in_background: true` (one notification when the condition holds) or with `Monitor` (one event per occurrence), never with a foreground `sleep`, `gh run watch` or a polling loop in the session's own shell.

**Why:** the user said so on 2026-09-14: "use monitor or background shells rather than sleep in the session itself. using sleep sequesters the session and effectively kills the reminders." Cron reminders fire only while the REPL is idle; a foreground wait holds it busy for the whole run, so the standing rules stop arriving exactly when they are most needed.

**How to apply:** start the wait in the background, end the turn, and act on the completion notification. The waiting rule in [[the-migration-outranks-10ulabs-com]] and "do nothing but wait while a workflow is running" still hold: idle means idle, not doing other work meanwhile.

A polling loop's exit test reads the run list from a here-string, never from a pipe into `grep -q`. The shell runs under `pipefail`, and `grep -q` closes the pipe at its first match, so `echo` dies of SIGPIPE and the pipeline fails whatever grep found. The first wait for e57f236 ended that way with eleven runs still queued. Count the unfinished runs instead, as in `left=$(grep -cv '^completed' <<<"$out")`, and break when `$out` is non-empty and `$left` is `0`.

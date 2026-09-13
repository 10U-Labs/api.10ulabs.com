---
name: an-issue-is-closed-by-its-commit
description: "An issue is closed by a Closes #N line in the commit that solves it, one line per issue, never by a comment posted afterwards"
metadata:
  type: feedback
---

# An issue is closed by its commit

The commit that solves an issue closes it, through a `Closes #N` line in the
message. One line per issue: GitHub binds the keyword to a single reference, so
`Closes #1 and #2` closes #1 and leaves #2 open.

**Why:** there is no pull request to close anything, per
[commit-straight-to-main](commit-straight-to-main.md), so the commit message is
the only place the link can live. Naming the issue in prose, as "GitHub
issue #114.", references it without closing it, which is what leaves a solved
issue open and waiting for somebody to notice. Closing by hand afterwards, with a
comment saying which commit did it, is a second record of what the message
already says and it is not how this repository works.

**How to apply:** put the `Closes #N` lines in the message of the commit that
does the work, before the attribution lines. A commit that solves twelve issues
carries twelve of them. If the closing line was missed and the commit is already
pushed, answer it forward the way any other rejected push is answered, per
[a-rejected-push-is-fixed-forward](a-rejected-push-is-fixed-forward.md): carry
the lines in the next commit rather than amending a pushed message.

---
name: a-decision-rewrites-the-issue
description: "A person's decision on an issue is recorded by rewriting the issue's title and body, never by posting a comment; the `needs decision` label comes off with the rewrite"
metadata:
  node_type: memory
  type: feedback
  originSessionId: f3354de6-c86d-4b34-99f2-7a8f14ef01cf
  modified: 2026-10-05T04:06:11.239Z
---

# A decision rewrites the issue

When a person settles an issue labelled `needs decision`, the decision goes into the issue itself: its title is rewritten if the decision changes what the issue asks for, its body is rewritten to state what was decided and what the fix is, and the `needs decision` label is removed. No comment is posted.

**Why:** The user said so directly when a session offered to "post the decision" on #142. The issue is read as the current statement of the work, so it must say what is now true; a decision left in a comment leaves the body still asking the question it answered.

**How to apply:** On a decision, run `gh issue edit N --title ... --body-file ... --remove-label "needs decision"` before starting the work. The same holds for any other update to an issue: rewrite it, do not comment on it. This sits beside [[issues-have-no-house-style]], which governs how the rewritten body is shaped.

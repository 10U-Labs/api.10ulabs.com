---
name: an-issue-documents-a-problem-that-exists-today
description: "An issue is filed for something broken now; a limit that is near but not reached, such as headroom under a quota, is not filed, and is solved when a change actually meets it"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 472cbef9-7ad3-4c85-a471-ab7fb2c8fffc
  modified: 2026-10-08T11:32:30.213Z
---

# An issue documents a problem that exists today

An issue is filed for something that is broken now. A limit that is close but not yet reached is a risk, not a problem, and gets no issue: a quota with little headroom left, or a size cap the next addition might cross. When a change actually meets the limit, the refusal is the problem, and it is solved then, in the work that met it.

**Why:** On 2026-10-08, after a grant was refused for exceeding IAM's 10240-byte inline-policy cap and squeezed under it, #267 was filed because the deploy role was left 227 bytes under the cap. It was labelled `bug` and `needs decision`. The user's view was that it was not a problem today, since nothing was refused once the grant landed, and they closed it as not planned.

**How to apply:** Before filing what you find ([[issues-have-no-house-style]], [[an-issue-is-split-by-problem-not-by-fix]]), ask whether something fails today. If it only might fail on a future addition, do not file it, and do not label it `needs decision` ([[a-decision-rewrites-the-issue]]). The commit that met the limit can record the measurement in its message.

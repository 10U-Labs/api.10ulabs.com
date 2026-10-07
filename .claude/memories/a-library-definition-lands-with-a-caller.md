---
name: a-library-definition-lands-with-a-caller
description: "assert-python-definition-is-used refuses a lib/python definition nothing names outside its own tests, so a new one lands with a caller and a dropped one leaves with its last caller, in one push"
metadata:
  node_type: memory
  type: feedback
  originSessionId: bf55e534-a8df-4c39-8a71-4a6fd6d11260
  modified: 2026-10-07T12:39:56.780Z
---

# A library definition lands with a caller

Every workflow runs `assert-python-definition-is-used` over `lib/python`, searching `src`, `test` and `lib/python` for a name each definition is called by, with the definition's own tests left out of the search. A definition nothing else names is a finding, and the finding fails every workflow before any stack reconciles.

**Why:** 90aa6f1 pushed `store.reserve` and its tests alone, as [[a-push-solves-every-open-issue-of-one-stack]] asks of a `lib/python` change, with its first caller meant for the carriers push after it. All eleven workflows went red on `Unused: lib/python/store/__init__.py:54:reserve`. The fix forward, ac786c8, routed `next_id` through `reserve` so that the library itself named it.

**How to apply:**

- A new library definition pushed alone needs a caller inside `lib/python` in the same commit, such as an existing function rewritten to go through it.
- When nothing in `lib/python` can call it, the definition and its first caller go in one commit, pushed with nothing else.
- Deleting a definition is the mirror: the last caller moves off it in the same commit that deletes it, since either half alone goes red.

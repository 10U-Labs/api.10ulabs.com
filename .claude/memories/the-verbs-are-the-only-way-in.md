---
name: the-verbs-are-the-only-way-in
description: There is no seed and no loader; every write is an HTTP verb backed by a Lambda handler, and a collection's workflow calls those verbs on a push to the data it serves, for what changed only
metadata:
  type: feedback
---

# The verbs are the only way in

There is no seed script, no `seeding` workflow and no loader. The API is its HTTP verbs, each a Lambda handler, and every caller uses them the same way. A collection's workflow is one such caller: on a push touching the data that collection serves, it calls the verbs for what the push changed and nothing else. A push to `data/pops/**` or `data/fiber_segments/**` has the `carriers` workflow call `DELETE` and `POST` for those carriers; a push to `data/hyperscale_cloud_service_providers/**` has the `hyperscale_cloud_service_providers` workflow do the same for the providers; a push to `etc/**` has the `wan_syntheses` workflow `POST` one synthesis per changed file.

**Why:** `wan-synthesizer`'s `scripts/seed.py` is one program that reloads every collection on every run, which the user rejects as against the Unix philosophy: one tool, one job, triggered by its own input. A loader beside the verbs is the same mistake in smaller pieces, a second door into the store; the verbs are the door, and a Lambda is called the same by a workflow as by anyone.

**How to apply:** where an issue says "the seed", read it as the workflow of the collection at hand calling that collection's verbs, and name the workflow. Do not write a script that dispatches over collections, do not add a loader Lambda or a `load.py`, and do not give a workflow a data trigger outside the files its collection serves; `openapi.json` is not one. What the verbs write is priced by [the-cheapest-backend-wins](the-cheapest-backend-wins.md).

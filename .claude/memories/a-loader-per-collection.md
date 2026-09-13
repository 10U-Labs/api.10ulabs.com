---
name: a-loader-per-collection
description: There is no seed; each collection has its own loader beside its endpoint, run by its own workflow on a push to the data it serves, loading only what changed
metadata:
  type: feedback
---

# A loader per collection

There is no seed script and no `seeding` workflow. Each collection has its own loader beside its endpoint, run by its own workflow, triggered by the files that collection serves: a push to `data/pops/**` or `data/fiber_segments/**` runs the carriers loader, a push to `data/hyperscale_cloud_service_providers/**` runs the providers loader, a push to `etc/**` runs the syntheses loader. A loader touches only what the push changed and nothing else.

**Why:** `wan-synthesizer`'s `scripts/seed.py` reloads every carrier, provider and tenant on every run, so a change to one file rewrites everything and a push that changes nothing still writes it all. That is one program doing every job, against the Unix philosophy the user holds to: one tool, one job, triggered by its own input.

**How to apply:** when an issue says "the seed", read it as the loader of the collection at hand and name that loader. Do not write a script that dispatches over collections, and do not give a loader's workflow a trigger path outside the data it serves; `openapi.json` in particular is not a loader trigger. What a loader writes is priced by [the-cheapest-backend-wins](the-cheapest-backend-wins.md).

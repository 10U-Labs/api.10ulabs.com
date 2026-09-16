---
name: this-repo-serves-routes-and-loads-nothing
description: api.10ulabs.com serves REST routes and nothing else; the data and the ETLs that load it live in wan-synthesizer, one ETL per dataset, fired by a push to the CSVs it reads
metadata:
  type: feedback
---

# This repo serves routes and loads nothing

`api.10ulabs.com` creates REST APIs. It holds no data and no loading. A
workflow here is lint, tests, reconciliation and post-deployment tests for one
endpoint; it never calls the deployed routes to put data in them, and it never
has a `data/**` or `etc/**` path in its trigger.

The data lives in `wan-synthesizer`, with an ETL per dataset that a push to
that dataset's CSVs fires, each a tool doing one job. An ETL calls this API's
verbs like any other caller.

**Why:** the user's own words are "this repo is solely about creating REST
APIs, no loading" and "that repo should be the one with different ETLs".
An earlier session drew the opposite conclusion from the same Unix-philosophy
reasoning, wrote it down as `the-verbs-are-the-only-way-in`, and then built
issues, commits and three reload jobs on top of it; the memory kept the
mistake alive across sessions. The reasoning was right and the placement was
wrong: one tool one job means an ETL per dataset in the data's repo, not a
loading job bolted onto each endpoint's workflow.

**How to apply:** where an issue says the workflow loads, seeds or reloads a
collection, that part belongs in `wan-synthesizer` as an ETL and the issue is
to be corrected before it is built. Nothing under `data/` or `etc/` belongs
here. Note that the issues in this repository were written by earlier sessions
under the user's credentials, so GitHub authorship proves nothing about whose
idea something was.

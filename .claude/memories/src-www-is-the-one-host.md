---
name: src-www-is-the-one-host
description: src/www is api.10ulabs.com itself, so its files sit directly there — openapi.json at src/www/openapi.json, no src/www/api
metadata:
  type: feedback
---

This repository serves one host, `api.10ulabs.com`, so `src/www` is that host and what it serves sits directly under it: the API description is `src/www/openapi.json`. There is no `src/www/api` and no other sub-site directory.

**Why:** The user asked on 2026-09-13 "why does 'www/api' exist when this repo hosts only 1 www (https://api.10ulabs.com)?" — the nesting was copied from `10ulabs.com`, where `www/` holds a site and the API sat beside it. Here the extra level names nothing.

**How to apply:** Reference the description as `src/www/openapi.json` (the routing stack's `templatefile`, the routing unit conftest, and each workflow's `src/www/**` path filter already do). A layout brought over from `10ulabs.com` is flattened to this repository's one host before it is committed. Related: [[no-v1-in-any-api-or-url]], [[one-gitignore-at-the-root]].

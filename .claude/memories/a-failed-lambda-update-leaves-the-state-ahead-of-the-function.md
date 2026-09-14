---
name: a-failed-lambda-update-leaves-the-state-ahead-of-the-function
description: A reconciliation that fails updating a Lambda's configuration records the planned source_code_hash without uploading the code, so the next reconciliation has nothing to upload; the fix forward must change the zip, and a description is 256 characters at most
metadata:
  type: feedback
---

# A failed Lambda update leaves the state ahead of the function

The AWS provider updates a Lambda's configuration before its code. When the configuration call is refused, the code is never uploaded, yet the state is saved with the planned `source_code_hash`, so the following reconciliation plans only the configuration, applies it, and reports success while the function still runs the code from before the red commit.

**Why:** On 2026-09-14 `ee660ea` (GET one run region, #48) lengthened the wan syntheses Lambda's description to 277 characters; Lambda refuses one over 256, so `d3ceca5`'s reconciliation planned the new hash, failed on `UpdateFunctionConfiguration`, and kept the hash. `055ff2f` shortened the description, reconciled "1 changed", and its deployed tests met a function without the new route, answering `Not found`. `65fa65c` changed the handler for real, the plan showed `source_code_hash` moving, and the route was served.

**How to apply:** Keep a Lambda's `description` under 256 characters. When a reconciliation fails partway through an `aws_lambda_function` update whose plan moved `source_code_hash`, the fix forward is not done until a plan uploads the code again: make the fix a genuine change inside the zip (`handler.py` or `lib/python/**`), and read the reconciliation log for `source_code_hash` moving before trusting the green. Related: [[a-fix-forward-fires-every-stack-the-red-commit-changed]], [[a-rejected-push-is-fixed-forward]].

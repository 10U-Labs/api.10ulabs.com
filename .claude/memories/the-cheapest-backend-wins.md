---
name: the-cheapest-backend-wins
description: A storage or service choice is decided by monthly cost alone, counted in fractions of a cent; maintenance effort is not a factor, and the always-free tier makes provisioned DynamoDB cost nothing where S3 never does
metadata:
  type: feedback
---

# The cheapest backend wins

A choice between backends is decided by what it adds to the monthly bill and nothing else. Pennies count: $0.002 beats $0.01. The effort of running a second store, a second IAM shape or a second read path does not weigh against it, because nothing is maintained by hand; it is all GitOps.

**Why:** the bill must stay under $1 a month, and half of that is the Route 53 hosted zone. The account is on the legacy always-free tier, which gives DynamoDB 25 GB and 25 provisioned read and write units for nothing, while S3 bills every request from the first one. So the store is one provisioned DynamoDB table (#14), its units summed with #8 and #12 to stay under 25, with no point-in-time recovery or backup where the seed rebuilds the data; S3 is kept only where CloudFront needs an origin.

**How to apply:** when an issue offers two ways to hold or serve something, price both at the real volumes before proposing either, and take the cheaper one even when the difference is a fraction of a cent. Do not argue simplicity, consistency or a single store against a smaller number. Writes are rare, since a workflow calls the verbs only for what a push changed, per [the-verbs-are-the-only-way-in](the-verbs-are-the-only-way-in.md), and the syntheses read the catalog through the API; the free tier is never approached.

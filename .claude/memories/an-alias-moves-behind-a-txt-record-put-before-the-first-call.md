---
name: an-alias-moves-behind-a-txt-record-put-before-the-first-call
description: A CloudFront alias moves between two distributions of the account with associate-alias, which checks a `_<alias>` TXT record naming the target's domain; put the record and let it resolve before the first call, since a refusal is cached for the zone's negative TTL
metadata:
  type: project
---

# An alias moves behind a TXT record put before the first call

`aws cloudfront associate-alias --alias <name> --target-distribution-id <id>` takes an alternate domain name off the distribution that holds it and puts it on the target in one step, so a name keeps answering throughout: CloudFront routes each request by its `Host` header to the distribution owning the alias, whatever the DNS record still points at, and the record is moved afterwards. Declaring the alias on the target instead fails with `CNAMEAlreadyExists`, and dropping it from the source first leaves the name answering 403 until the target's update completes.

**Why:** On 2026-09-15 the cut-over of `api.10ulabs.com` (#117) called `associate-alias` before any TXT record existed and was refused `IllegalUpdate: Invalid or missing alias DNS TXT records`; the record `_api.10ulabs.com TXT "d1r7tul68ehxbn.cloudfront.net"` was then put in the zone and resolved at once, but the call was refused again, and only succeeded fifteen minutes later — the zone's negative-caching TTL — once CloudFront's resolver had forgotten the first miss. The record is deleted once the alias has moved; nothing declares it.

**How to apply:** Before the first `associate-alias`, upsert `_<alias>` TXT in the zone with the target distribution's domain name as its value, `aws route53 wait resource-record-sets-changed` on the change, and confirm `dig +short TXT _<alias>` answers; only then call `associate-alias`, from the operator's own credentials since the deploy role is not granted `cloudfront:AssociateAlias`. A cut-over that first deploys the target without the alias and then declares it is two declared states, so it is two pushes of this repository with the closing `Closes #N` on the second; the stack that loses the alias is applied by hand between them, after `tofu state rm` of the record it must stop managing so that this repository's `allow_overwrite = true` record takes it over. Related: [[a-by-hand-destroy-follows-the-push-that-drops-the-workflow]], [[the-migration-outranks-10ulabs-com]].

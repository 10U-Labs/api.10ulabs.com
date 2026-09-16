---
name: a-custom-error-response-answers-for-every-origin
description: A CloudFront custom_error_response is distribution-wide, so it replaces the gateway's own 404s too; a friendly page belongs in the catch-all handler, which alone knows no route matched
metadata:
  type: project
---

# A custom error response answers for every origin

`custom_error_response` sits on the distribution, not on a behaviour, so
`response_page_path` answers every origin's error of that code. On a distribution
that fronts both the host's bucket and the API gateway, a 404 page for unmatched
paths therefore swallows the API's own refusals: the bodies clients read, such as
`{"error": "No such carrier"}`, arrive as HTML.

**Why:** On 2026-09-14 `eb6397a` and `5fd48ad` gave `api.10ulabs.com` a
`custom_error_response` naming `/404.html`, and
`GET https://api.10ulabs.com/carriers/999999999` then answered the page instead of
the gateway's JSON, while the same request to the stage URL answered correctly, so
no endpoint test saw it. `5a20564` removed the block and moved the page into the
catch-all handler, which answers it only when the request's `Accept` holds
`text/html` and JSON otherwise; the page reaches the handler as a Lambda
environment variable holding the text of `src/www/404.html`, which keeps one copy
of the page and lets the unit tests set it.

**How to apply:** Never answer a friendly page from the distribution when an origin
behind it speaks JSON. Let the origin that knows the request matched nothing — here
the gateway's catch-all — answer, and pick the media type from `Accept`. Related:
[[src-www-is-the-one-host]], [[the-stacks-are-opentofu]].

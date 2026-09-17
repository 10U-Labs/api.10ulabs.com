---
name: a-raise-expected-in-a-test-is-raised-in-a-fixture
description: "assert-one-assert-per-pytest counts a `with pytest.raises` as an assert, so a test that expects a raise and asserts on what followed moves the raising call into a fixture and keeps the one assert"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 9e3c5421-3b58-49e5-b494-8ecfd9440ef1
  modified: 2026-09-17T07:27:38.539Z
---

# A raise expected in a test is raised in a fixture

`assert-one-assert-per-pytest` counts a `with pytest.raises(...)` block as an assert, so a test that both expects a call to raise and asserts on a side effect afterwards holds two and is refused.

**Why:** On 2026-09-17 `3f78ec6` added `test_a_store_that_refuses_the_first_mark_invalidates_nothing`, which wrapped the synthesizer's call in `pytest.raises(ClientError)` and then asserted nothing was invalidated; the gate reported the test at 2 and the wan-syntheses workflow went red on it alone. `0f6e157` moved the raising call into an `unmarked` fixture and left the test with its one assert.

**How to apply:** Put the call that is expected to raise, with its `pytest.raises`, in a fixture the test requests through `usefixtures`, and assert on the outcome in the test. Related: [[a-fixture-consumed-in-its-own-file-is-named]], [[write-the-test-first]].

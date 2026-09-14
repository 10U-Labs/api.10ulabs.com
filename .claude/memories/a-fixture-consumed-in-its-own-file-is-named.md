---
name: a-fixture-consumed-in-its-own-file-is-named
description: A pytest fixture requested by a test or fixture in the file that defines it is declared with name= on a *_fixture function; one requested only from other files is a plain def, since pylint's W0621 and assert-pytest-fixture-name-is-needed pull opposite ways
metadata:
  type: feedback
---

# A fixture consumed in its own file is named

Two gates meet at a fixture's name. pylint's `redefined-outer-name` (W0621) fires when a function's parameter carries the same name as a module-level function, so a fixture `def bearer()` requested as `bearer` by a test or another fixture in the same file is red. `assert-pytest-fixture-name-is-needed` fires when `name=` is given and nothing in that file binds the name, so a fixture nothing in its own file requests is red the other way round.

**Why:** On 2026-09-14 `eb7afe1` added `read_json(stage_url, get_json, bearer)` to `test/api/conftest.py`, where those three were plain fixtures consumed only by other files until then; pylint-tests went red on every workflow that lints tests, and `07e03b2` renamed them `*_fixture` with `name=`. Earlier, `478e816` had gone the other way: `name=` on fixtures nothing in their file requested.

**How to apply:** When a fixture is requested within the file that defines it (a test parameter, a fixture parameter), declare it `@pytest.fixture(name="x")` on `def x_fixture(...)`; `usefixtures("x")` does not bind the name and does not count. When it is requested only from other files, declare it `@pytest.fixture` on `def x(...)`. Adding a consumer inside the file means renaming the fixture in the same commit. Related: [[write-the-test-first]], [[ci-is-the-source-of-truth]].

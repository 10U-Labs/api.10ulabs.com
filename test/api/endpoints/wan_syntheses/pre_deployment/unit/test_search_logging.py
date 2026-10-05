from __future__ import annotations

import re

import pytest

import fixtures
from synthesizer.synthesize import synthesize_two_tier


def _logged(caplog: pytest.LogCaptureFixture) -> list[str]:
    with caplog.at_level("INFO"):
        synthesize_two_tier(
            fixtures.ring_pops(), fixtures.ring_fiber_segments(), fixtures.ring_params()
        )
    return [record.getMessage() for record in caplog.records]


def test_backbone_scan_logs_a_progress_heartbeat(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr("synthesizer.synthesize._SEARCH_LOG_INTERVAL", 1)
    assert any("scanned" in message for message in _logged(caplog))


def test_the_search_logs_the_sites_and_the_provider_regions_apart(
    caplog: pytest.LogCaptureFixture
) -> None:
    assert any(
        re.match(r"Synthesizing \d+ sites and \d+ provider regions;", message)
        for message in _logged(caplog)
    )

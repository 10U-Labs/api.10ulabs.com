from typing import Dict, Optional, Tuple
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

API_NAME = "api.10ulabs.com"
MAP = "https://www.10ulabs.com"
SYNTHESES = "/wan-syntheses"
MAP_READS = [
    SYNTHESES,
    *(f"{SYNTHESES}/1/{part}" for part in (
        "wan-pops", "sites", "hyperscale-cloud-service-provider-regions", "fiber-segments",
        "homing-circuits", "backbone-circuits",
    )),
]
ASKING = {
    "Origin": MAP,
    "Access-Control-Request-Method": "GET",
    "Access-Control-Request-Headers": "authorization",
}
REFUSED = {"Authorization": "Bearer not-the-key"}


def _allowed(
    path: str, headers: Dict[str, str], method: str = "GET"
) -> Tuple[int, Optional[str]]:
    request = Request(f"https://{API_NAME}{path}", headers=headers, method=method)
    try:
        with urlopen(request, timeout=10) as response:
            return int(response.status), response.headers.get("Access-Control-Allow-Origin")
    except HTTPError as error:
        return error.code, error.headers.get("Access-Control-Allow-Origin")


@pytest.mark.parametrize("path", MAP_READS)
def test_a_preflight_to_a_route_the_map_reads_allows_the_map(path: str) -> None:
    assert _allowed(path, ASKING, "OPTIONS") == (200, MAP)


def test_a_read_the_map_makes_is_allowed_to_the_map(bearer: Dict[str, str]) -> None:
    assert _allowed(SYNTHESES, {**bearer, "Origin": MAP}) == (200, MAP)


def test_a_refused_token_on_a_route_the_map_reads_is_shown_to_the_map() -> None:
    assert _allowed(SYNTHESES, {**REFUSED, "Origin": MAP}) == (401, MAP)

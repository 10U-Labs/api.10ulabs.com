from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

import pytest
import yaml

from published_syntheses import published_synthesis


@pytest.fixture(scope="session")
def runs(repo_root: Path) -> Dict[str, Dict[str, Any]]:
    return {
        path.stem.replace("_", "-"): yaml.safe_load(path.read_text(encoding="utf-8"))
        for path in sorted((repo_root / "etc").glob("*.yml"))
    }


@pytest.fixture(scope="session", name="delivered_syntheses")
def delivered_syntheses_fixture(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str],
    runs: Dict[str, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    def read(path: str) -> Any:
        return get_json(f"{stage_url}{path}", bearer)[1]
    return [published_synthesis(read, config["label"], config) for config in runs.values()]


@pytest.fixture(scope="session")
def published_syntheses(delivered_syntheses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        synthesis for synthesis in delivered_syntheses
        if synthesis["status"].get("status") == "success"
    ]

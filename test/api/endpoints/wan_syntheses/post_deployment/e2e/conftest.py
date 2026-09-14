from pathlib import Path
from typing import Any, Callable, Dict, List

import pytest
import yaml

from published_syntheses import published_synthesis


@pytest.fixture(scope="session", name="runs")
def runs_fixture(repo_root: Path) -> Dict[str, Dict[str, Any]]:
    return {
        path.stem.replace("_", "-"): yaml.safe_load(path.read_text(encoding="utf-8"))
        for path in sorted((repo_root / "etc").glob("*.yml"))
    }


@pytest.fixture(scope="session", name="delivered_syntheses")
def delivered_syntheses_fixture(
    read_json: Callable[[str], Any], runs: Dict[str, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    return [
        published_synthesis(read_json, config["label"], config) for config in runs.values()
    ]


@pytest.fixture(scope="session")
def published_syntheses(delivered_syntheses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        synthesis for synthesis in delivered_syntheses
        if synthesis["status"].get("status") == "success"
    ]

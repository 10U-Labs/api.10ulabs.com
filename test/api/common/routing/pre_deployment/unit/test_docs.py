from pathlib import Path

import pytest


@pytest.fixture(scope="module", name="docs_page")
def docs_page_fixture(repo_root: Path) -> str:
    return (repo_root / "src" / "www" / "index.html").read_text(encoding="utf-8")


def test_the_documentation_page_renders_the_spec_beside_it(docs_page: str) -> None:
    assert "Redoc.init('openapi.json'" in docs_page


def test_the_documentation_page_is_titled_for_the_api(docs_page: str) -> None:
    assert "<title>10U Labs API Documentation</title>" in docs_page


@pytest.fixture(scope="module", name="not_found_page")
def not_found_page_fixture(repo_root: Path) -> str:
    return (repo_root / "src" / "www" / "404.html").read_text(encoding="utf-8")


def test_the_not_found_page_points_back_to_the_documentation(not_found_page: str) -> None:
    assert '<a href="/">View API Documentation</a>' in not_found_page

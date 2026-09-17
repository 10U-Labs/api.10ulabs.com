from pathlib import Path

import pytest


@pytest.fixture(scope="module", name="index_page")
def index_page_fixture(repo_root: Path) -> str:
    return (repo_root / "src" / "www" / "index.html").read_text(encoding="utf-8")


def test_the_index_page_renders_the_spec_beside_it(index_page: str) -> None:
    assert "Redoc.init('openapi.json'" in index_page


def test_the_index_page_is_titled_for_the_api(index_page: str) -> None:
    assert "<title>10U Labs API</title>" in index_page


@pytest.fixture(scope="module", name="not_found_page")
def not_found_page_fixture(repo_root: Path) -> str:
    return (repo_root / "src" / "www" / "404.html").read_text(encoding="utf-8")


def test_the_not_found_page_is_titled_for_the_api(not_found_page: str) -> None:
    assert "<title>10U Labs - 404 Not Found</title>" in not_found_page


def test_the_not_found_page_points_back_to_the_index(not_found_page: str) -> None:
    assert '<a href="/">10U Labs API</a>' in not_found_page

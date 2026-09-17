import re
from pathlib import Path

import pytest

BLOCK = r'resource "terraform_data" "invalidation" \{.*?\n\}'
TRIGGERS = r"triggers_replace\s*=\s*\[(.*?)\]"
CREATE = "create-invalidation --distribution-id ${aws_cloudfront_distribution.api.id} --paths '/*'"


@pytest.fixture(scope="module", name="invalidation")
def invalidation_fixture(routing_dir: Path) -> str:
    cloudfront_tf = (routing_dir / "cloudfront.tf").read_text(encoding="utf-8")
    match = re.search(BLOCK, cloudfront_tf, re.DOTALL)
    return "" if match is None else match.group(0)


@pytest.fixture(scope="module", name="triggers")
def triggers_fixture(invalidation: str) -> list[str]:
    match = re.search(TRIGGERS, invalidation, re.DOTALL)
    return [] if match is None else match.group(1).replace(",", " ").split()


def test_the_stack_invalidates_the_distribution(invalidation: str) -> None:
    assert invalidation.startswith('resource "terraform_data" "invalidation"')


def test_the_invalidation_is_triggered_by_the_files_fingerprints(triggers: list[str]) -> None:
    assert triggers == [
        "aws_s3_object.index.etag",
        "aws_s3_object.spec.etag",
        "aws_s3_object.not_found.etag",
    ]


def test_the_invalidation_covers_every_path_of_the_distribution(invalidation: str) -> None:
    assert CREATE in invalidation


def test_the_invalidation_is_waited_for(invalidation: str) -> None:
    assert "aws cloudfront wait invalidation-completed" in invalidation

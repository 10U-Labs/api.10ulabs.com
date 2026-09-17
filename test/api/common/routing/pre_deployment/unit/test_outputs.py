import re
from pathlib import Path

DISTRIBUTION_ID = r'output "distribution_id" \{[^}]*value\s*=\s*aws_cloudfront_distribution\.api\.id'


def test_the_stack_exports_the_distribution_id(routing_dir: Path) -> None:
    outputs_tf = (routing_dir / "outputs.tf").read_text(encoding="utf-8")
    assert re.search(DISTRIBUTION_ID, outputs_tf)

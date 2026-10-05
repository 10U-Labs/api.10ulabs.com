import re
from pathlib import Path

RETENTION = r"retention_in_days\s*=\s*(\d+)"


def test_every_log_group_the_stack_declares_is_kept_five_years(repo_root: Path) -> None:
    stack = repo_root / "src/api/endpoints/contact_submissions"
    declared = "".join(path.read_text(encoding="utf-8") for path in stack.glob("*.tf"))
    assert set(re.findall(RETENTION, declared)) == {"1827"}

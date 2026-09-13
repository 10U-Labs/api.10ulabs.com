from pathlib import Path
from typing import Any, Iterator

import yaml

DECLARED_ROLE = "${{ vars.OIDC_ROLE_ARN }}"


def _credential_steps(repo_root: Path) -> Iterator[Any]:
    for workflow in sorted((repo_root / ".github" / "workflows").glob("*.yml")):
        jobs = yaml.safe_load(workflow.read_text(encoding="utf-8"))["jobs"]
        for job in jobs.values():
            for step in job["steps"]:
                if "configure-aws-credentials" in step.get("uses", ""):
                    yield step


def test_every_credential_step_assumes_the_declared_role(repo_root: Path) -> None:
    steps = _credential_steps(repo_root)
    assert all(step["with"]["role-to-assume"] == DECLARED_ROLE for step in steps)


def test_at_least_one_workflow_assumes_a_role(repo_root: Path) -> None:
    assert sum(1 for _ in _credential_steps(repo_root)) > 0


def test_every_workflow_that_assumes_a_role_calls_aws_over_fips_endpoints(repo_root: Path) -> None:
    workflows = [
        yaml.safe_load(path.read_text(encoding="utf-8"))
        for path in (repo_root / ".github" / "workflows").glob("*.yml")
        if "configure-aws-credentials" in path.read_text(encoding="utf-8")
    ]
    assert all(workflow["env"]["AWS_USE_FIPS_ENDPOINT"] == "true" for workflow in workflows)

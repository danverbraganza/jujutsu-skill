"""Write one Harbor task directory per scenario.

Each task gets its own copy of this package in all three parts: the image build runs `setup`,
the verifier runs `check`, and Harbor's oracle agent runs `solve`. Harbor copies `tests/` and
`solution/` in only after the agent finishes, so the agent never sees the checks.
"""

import json
import shutil
from pathlib import Path

from jj_eval.scenario import Scenario

PACKAGE = Path(__file__).resolve().parent
TEMPLATES = PACKAGE / "docker"

TASK_TOML = """schema_version = "1.4"

[metadata]
tags = {tags}

[agent]
timeout_sec = 900.0

[verifier]
timeout_sec = 300.0
environment_mode = "shared"

[environment]
build_timeout_sec = 900.0
"""

SCRIPT = """#!/bin/bash
cd "$(dirname "$0")" && python3 -m jj_eval {command} {name}
"""


def write_tasks(scenarios: list[type[Scenario]], jj_version: str, out_dir: Path) -> Path:
    """Replace `out_dir` with one task per scenario, each building its repo with jj `jj_version`."""
    if out_dir.exists():
        shutil.rmtree(out_dir)
    for scenario in scenarios:
        task = out_dir / scenario.name
        for part in ("environment", "tests", "solution"):
            shutil.copytree(PACKAGE, task / part / "jj_eval", ignore=shutil.ignore_patterns("__pycache__", "docker"))
        environment = task / "environment"
        dockerfile = (TEMPLATES / "Dockerfile").read_text()
        dockerfile = dockerfile.replace("@JJ_VERSION@", jj_version).replace("@SCENARIO@", scenario.name)
        (environment / "Dockerfile").write_text(dockerfile)
        for helper in ("jj-shim", "jj-eval-editor", "jj-config.toml"):
            shutil.copy2(TEMPLATES / helper, environment / helper)
        (task / "instruction.md").write_text(scenario.prompt + "\n")
        (task / "task.toml").write_text(TASK_TOML.format(tags=json.dumps(list(scenario.tags))))
        for script, command in ((task / "tests" / "test.sh", "check"), (task / "solution" / "solve.sh", "solve")):
            script.write_text(SCRIPT.format(command=command, name=scenario.name))
            script.chmod(0o755)
    return out_dir

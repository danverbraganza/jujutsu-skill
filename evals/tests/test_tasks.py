import os
import re

import pytest

from jj_eval.scenarios import SCENARIOS
from jj_eval.tasks import write_tasks


def test_each_scenario_becomes_a_harbor_task(tmp_path):
    chosen = [SCENARIOS["create-bookmark"], SCENARIOS["push-new-bookmark"]]
    write_tasks(chosen, "0.46.0", tmp_path)

    assert sorted(p.name for p in tmp_path.iterdir()) == ["create-bookmark", "push-new-bookmark"]
    task = tmp_path / "create-bookmark"
    assert (task / "instruction.md").read_text() == SCENARIOS["create-bookmark"].prompt + "\n"
    dockerfile = (task / "environment" / "Dockerfile").read_text()
    assert "ARG JJ_VERSION=0.46.0" in dockerfile and "setup create-bookmark" in dockerfile
    assert 'environment_mode = "shared"' in (task / "task.toml").read_text()
    for script, command in (("tests/test.sh", "check"), ("solution/solve.sh", "solve")):
        assert f"jj_eval {command} create-bookmark" in (task / script).read_text()
        assert os.access(task / script, os.X_OK)


def test_every_part_of_a_task_carries_its_own_copy_of_the_scenarios(tmp_path):
    write_tasks([SCENARIOS["create-bookmark"]], "0.37.0", tmp_path)

    for part in ("environment", "tests", "solution"):
        package = tmp_path / "create-bookmark" / part / "jj_eval"
        assert (package / "scenarios" / "everyday.py").exists()
        assert not list(package.rglob("__pycache__"))


def test_writing_tasks_replaces_what_was_there(tmp_path):
    write_tasks([SCENARIOS["create-bookmark"]], "0.46.0", tmp_path)
    write_tasks([SCENARIOS["tag-release"]], "0.46.0", tmp_path)

    assert [p.name for p in tmp_path.iterdir()] == ["tag-release"]


@pytest.mark.parametrize("name", SCENARIOS)
def test_prompt_is_plain_language(name):
    prompt = SCENARIOS[name].prompt
    assert not re.search(r"\bjj\b", prompt), "prompts describe the goal; they never name jj commands"

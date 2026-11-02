import json
from dataclasses import asdict

from jj_eval.__main__ import main, run_label
from jj_eval.runner import Result
from jj_eval.scenarios import SCENARIOS


def test_list_prints_every_scenario_with_its_prompt(capsys):
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    for name, scenario in SCENARIOS.items():
        assert name in out and scenario.prompt in out


def test_run_label_names_the_jj_version_model_and_skill():
    assert run_label("0.46.0", "sonnet", skill=True) == "jj-0.46.0-sonnet"
    assert run_label("0.37.0", "opus", skill=False) == "jj-0.37.0-opus-no-skill"


def test_compare_tells_apart_runs_whose_directories_share_a_name(tmp_path, capsys):
    run_dirs = []
    for label, passed in (("before", False), ("after", True)):
        run_dir = tmp_path / label / "jj-0.46.0-sonnet"
        run_dir.mkdir(parents=True)
        run = Result(
            scenario="tag-release", trial=1, jj_version="0.46.0", model="sonnet", passed=passed,
            failure=None if passed else "it broke", agent_status="success", duration_s=1.0, turns=1,
            cost_usd=0.0, skill_invoked=True, jj_calls=1, jj_failures=[], warnings=[], editor_prompts=0,
            git_commands=[], final_message=None, sandbox="",
        )
        (run_dir / "results.json").write_text(json.dumps([asdict(run)]))
        run_dirs.append(str(run_dir))

    assert main(["compare", *run_dirs]) == 0
    out = capsys.readouterr().out
    assert "| Scenario | before/jj-0.46.0-sonnet | after/jj-0.46.0-sonnet |" in out
    assert "| tag-release | FAIL | pass |" in out

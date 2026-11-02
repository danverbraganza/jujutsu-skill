import json
import subprocess

from jj_eval.agent import AgentRun, Transcript
from jj_eval.runner import Options, Result, compare, failed_calls, run_scenario, summarize
from jj_eval.sandbox import Invocation
from jj_eval.scenarios import SCENARIOS


def fake_agent(*commands):
    """An agent that runs fixed jj commands through the sandbox's shim instead of thinking."""

    def agent(prompt, *, cwd, env, transcript_path, **_):
        for args in commands:
            subprocess.run(["jj", *args], cwd=cwd, env=env, capture_output=True)
        transcript_path.write_text("")
        return AgentRun(Transcript(), exit_code=0, timed_out=False, duration_s=1.0)

    return agent


def run(tmp_path, jj, agent):
    options = Options(model="fake", skill_dir=None)
    return run_scenario(SCENARIOS["create-bookmark"], jj, tmp_path / "run", options, agent=agent)


def test_a_run_passes_when_the_agent_reaches_the_end_state(tmp_path, jj):
    result = run(tmp_path, jj, fake_agent(["bookmark", "create", "feature-login", "-r", "@-"]))

    assert result.passed and result.failure is None
    assert result.jj_calls == 1 and result.jj_failures == []
    assert json.loads((tmp_path / "run" / "result.json").read_text())["passed"] is True


def test_a_run_reports_the_unmet_requirement_and_failed_jj_calls(tmp_path, jj):
    result = run(tmp_path, jj, fake_agent(["bookmark", "create", "feature-login", "-r", "no-such-revision"]))

    assert not result.passed
    assert "feature-login" in result.failure
    assert result.jj_failures == ["bookmark create feature-login -r no-such-revision"]


def result(scenario, passed, **overrides):
    fields = dict(
        scenario=scenario, trial=1, jj_version="0.46.0", model="sonnet", passed=passed,
        failure=None if passed else "it broke", agent_status="success", duration_s=12.0, turns=4,
        cost_usd=0.1, skill_invoked=True, jj_calls=3, jj_failures=[], warnings=[], editor_prompts=0,
        git_commands=[], final_message="Done.", sandbox="/tmp/x",
    )
    return Result(**{**fields, **overrides})


def test_summary_shows_the_pass_rate_and_each_failure():
    text = summarize([
        result("create-bookmark", True),
        result("tag-release", False, jj_failures=["tag set v1.0"], warnings=["Warning: deprecated"]),
    ])

    assert "1/2 passed" in text
    assert "| create-bookmark | pass |" in text
    assert "| tag-release | FAIL |" in text
    assert "it broke" in text and "`jj tag set v1.0`" in text and "Warning: deprecated" in text


def test_compare_lines_up_scenarios_across_runs():
    old = [result("create-bookmark", True), result("tag-release", True, jj_failures=["x", "y"])]
    new = [result("create-bookmark", True, jj_version="0.37.0"), result("tag-release", False, jj_version="0.37.0")]
    text = compare({"jj-0.46.0": old, "jj-0.37.0": new})

    assert "| Scenario | jj-0.46.0 | jj-0.37.0 |" in text
    assert "| tag-release | pass (2 failed jj calls) | FAIL |" in text


def test_a_jj_call_cut_off_by_a_closed_pipe_is_not_a_failure():
    calls = [Invocation(0, "st"), Invocation(1, "edit nope"), Invocation(3, "log -p --git")]

    assert failed_calls(calls) == ["edit nope"]

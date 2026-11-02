import json

from jj_eval.report import compare, load_trials, summarize


def make_trial(job_dir, scenario, suffix, rewards, failure=None, failed=(), exception=None, cost=0.25):
    trial = job_dir / f"{scenario}__{suffix}"
    (trial / "verifier").mkdir(parents=True)
    result = {
        "task_name": scenario,
        "verifier_result": {"rewards": rewards} if rewards else None,
        "agent_result": {"cost_usd": cost},
        "exception_info": exception,
    }
    (trial / "result.json").write_text(json.dumps(result))
    if rewards:
        detail = {"scenario": scenario, "failure": failure, "failed_jj_calls": list(failed)}
        (trial / "verifier" / "check.json").write_text(json.dumps(detail))


def job(tmp_path, name):
    job_dir = tmp_path / name
    make_trial(job_dir, "create-bookmark", "a", {"reward": 1, "jj_calls": 3, "failed_jj_calls": 0, "editor_prompts": 0})
    make_trial(
        job_dir, "push-new-bookmark", "b", {"reward": 0, "jj_calls": 4, "failed_jj_calls": 1, "editor_prompts": 0},
        failure="origin's search branch is not at 'Add search'", failed=["git push -b search"],
    )
    make_trial(job_dir, "tag-release", "c", None, exception={"exception_type": "AgentTimeoutError", "exception_message": "900s"})
    (job_dir / "result.json").write_text("{}")
    return job_dir


def test_load_trials_reads_harbor_results_and_our_check_details(tmp_path):
    trials = {t.scenario: t for t in load_trials(job(tmp_path, "jj-0.46.0-claude-code"))}

    assert trials["create-bookmark"].passed and trials["create-bookmark"].jj_calls == 3
    push = trials["push-new-bookmark"]
    assert not push.passed and push.failed_jj_calls == ["git push -b search"]
    assert "not at 'Add search'" in push.failure
    timeout = trials["tag-release"]
    assert not timeout.judged and not timeout.passed and "AgentTimeoutError" in timeout.failure
    assert push.judged


def test_summary_lists_failures_and_failed_jj_calls(tmp_path):
    text = summarize("jj-0.46.0-claude-code", load_trials(job(tmp_path, "jj-0.46.0-claude-code")))

    assert "1/3 passed" in text
    assert "| push-new-bookmark | FAIL | 4 | 1 |" in text
    assert "`jj git push -b search`" in text and "AgentTimeoutError" in text


def test_compare_lines_up_scenarios_across_jobs(tmp_path):
    runs = {name: load_trials(job(tmp_path, name)) for name in ("jj-0.37.0-claude-code", "jj-0.46.0-claude-code")}
    text = compare(runs)

    assert "| Scenario | jj-0.37.0-claude-code | jj-0.46.0-claude-code |" in text
    assert "| push-new-bookmark | FAIL (1 failed jj call) | FAIL (1 failed jj call) |" in text
    assert "| **passed** | 1/3 | 1/3 |" in text

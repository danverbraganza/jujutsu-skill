"""Summarize Harbor job directories: pass rates per scenario, and the jj calls that failed on the way."""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Trial:
    scenario: str
    judged: bool  # the verifier ran; False when the trial errored before grading
    passed: bool
    failure: str | None
    jj_calls: int
    failed_jj_calls: list[str]
    editor_prompts: int
    cost_usd: float | None


def load_trials(job_dir: Path) -> list[Trial]:
    """One Trial per trial directory, from Harbor's result.json and the check's own check.json."""
    trials = []
    for result_path in sorted(job_dir.glob("*/result.json")):
        result = json.loads(result_path.read_text())
        rewards = (result.get("verifier_result") or {}).get("rewards") or {}
        check_path = result_path.parent / "verifier" / "check.json"
        detail = json.loads(check_path.read_text()) if check_path.exists() else {}
        failure = detail.get("failure")
        if not rewards:
            exception = result.get("exception_info") or {}
            failure = f"no verdict: {exception.get('exception_type', 'unknown error')}: {exception.get('exception_message', '')}"
        trials.append(
            Trial(
                scenario=result["task_name"],
                judged=bool(rewards),
                passed=rewards.get("reward") == 1,
                failure=failure,
                jj_calls=int(rewards.get("jj_calls", 0)),
                failed_jj_calls=detail.get("failed_jj_calls", []),
                editor_prompts=int(rewards.get("editor_prompts", 0)),
                cost_usd=(result.get("agent_result") or {}).get("cost_usd"),
            )
        )
    return trials


def summarize(label: str, trials: list[Trial]) -> str:
    passed = sum(t.passed for t in trials)
    cost = sum(t.cost_usd or 0 for t in trials)
    lines = [
        f"# {label}",
        "",
        f"{passed}/{len(trials)} passed. Agent cost ${cost:.2f}.",
        "",
        "| Scenario | Result | jj calls | Failed jj calls | Editor prompts |",
        "|---|---|---|---|---|",
    ]
    for t in sorted(trials, key=lambda t: t.scenario):
        result = "pass" if t.passed else "FAIL"
        lines.append(f"| {t.scenario} | {result} | {t.jj_calls} | {len(t.failed_jj_calls)} | {t.editor_prompts} |")
    failures = [t for t in trials if not t.passed]
    if failures:
        lines += ["", "## Failures", ""] + [f"- **{t.scenario}**: {t.failure}" for t in failures]
    failed_calls = [(t.scenario, call) for t in trials for call in t.failed_jj_calls]
    if failed_calls:
        lines += ["", "## jj calls that exited non-zero", ""]
        lines += [f"- {scenario}: `jj {call}`" for scenario, call in failed_calls]
    return "\n".join(lines) + "\n"


def compare(runs: dict[str, list[Trial]]) -> str:
    """One row per scenario, one column per job."""
    labels = list(runs)
    names = sorted({t.scenario for trials in runs.values() for t in trials})
    lines = ["| Scenario | " + " | ".join(labels) + " |", "|---" * (len(labels) + 1) + "|"]
    for name in names:
        cells = [_cell([t for t in runs[label] if t.scenario == name]) for label in labels]
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    totals = [f"{sum(t.passed for t in runs[label])}/{len(runs[label])}" for label in labels]
    lines.append("| **passed** | " + " | ".join(totals) + " |")
    return "\n".join(lines) + "\n"


def _cell(trials: list[Trial]) -> str:
    if not trials:
        return "-"
    passed = sum(t.passed for t in trials)
    status = ("pass" if passed else "FAIL") if len(trials) == 1 else f"{passed}/{len(trials)} pass"
    failed_calls = sum(len(t.failed_jj_calls) for t in trials)
    if failed_calls:
        status += f" ({failed_calls} failed jj call{'' if failed_calls == 1 else 's'})"
    return status

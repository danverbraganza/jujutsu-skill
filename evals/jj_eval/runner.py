"""Run scenarios against an agent, then summarize and compare the results."""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from jj_eval.agent import run_claude
from jj_eval.binaries import jj_version
from jj_eval.repo import CheckFailure
from jj_eval.sandbox import Sandbox
from jj_eval.scenario import Scenario

SKILL_DIR = Path(__file__).resolve().parents[2] / "jujutsu"


@dataclass(frozen=True)
class Options:
    model: str = "sonnet"
    max_turns: int = 40
    timeout: float = 900
    skill_dir: Path | None = SKILL_DIR  # None runs the agent without the skill, as a baseline
    claude: str = "claude"


@dataclass
class Result:
    scenario: str
    trial: int
    jj_version: str
    model: str
    passed: bool
    failure: str | None
    agent_status: str
    duration_s: float
    turns: int | None
    cost_usd: float | None
    skill_invoked: bool
    jj_calls: int
    jj_failures: list[str]
    warnings: list[str]
    editor_prompts: int
    git_commands: list[str]
    final_message: str | None
    sandbox: str


def run_scenario(
    scenario_cls: type[Scenario], jj: Path, root: Path, options: Options, trial: int = 1, agent: Callable = run_claude
) -> Result:
    scenario = scenario_cls()
    sb = Sandbox.create(root, jj)
    scenario.setup(sb)
    plugin = sb.install_skill(options.skill_dir) if options.skill_dir else None
    run = agent(
        scenario.prompt,
        cwd=sb.repo_dir,
        env=sb.agent_env(),
        plugin_dir=plugin,
        model=options.model,
        max_turns=options.max_turns,
        timeout=options.timeout,
        transcript_path=sb.root / "transcript.jsonl",
        claude=options.claude,
    )
    failure = _check(scenario, sb)
    final = run.transcript.result or {}
    invocations = sb.jj_invocations()
    result = Result(
        scenario=scenario.name,
        trial=trial,
        jj_version=jj_version(jj),
        model=options.model,
        passed=failure is None,
        failure=failure,
        agent_status="timeout" if run.timed_out else final.get("subtype", f"exit {run.exit_code}"),
        duration_s=round(run.duration_s, 1),
        turns=final.get("num_turns"),
        cost_usd=final.get("total_cost_usd"),
        skill_invoked=run.transcript.skill_invoked,
        jj_calls=len(invocations),
        jj_failures=[i.args for i in invocations if i.status != 0],
        warnings=run.transcript.warnings(),
        editor_prompts=sb.editor_invocations(),
        git_commands=run.transcript.git_commands(),
        final_message=final.get("result"),
        sandbox=str(sb.root),
    )
    (sb.root / "result.json").write_text(json.dumps(asdict(result), indent=2) + "\n")
    return result


def _check(scenario: Scenario, sb: Sandbox) -> str | None:
    try:
        scenario.check(sb)
    except CheckFailure as failure:
        return str(failure)
    except Exception as error:  # a mangled repo can make the check's own jj calls fail
        return f"check crashed: {type(error).__name__}: {error}"
    return None


def run_all(
    scenarios: list[type[Scenario]],
    jj: Path,
    out_dir: Path,
    options: Options,
    *,
    trials: int = 1,
    jobs: int = 4,
    on_result: Callable[[Result, int, int], None] = lambda result, done, total: None,
) -> list[Result]:
    """Run every scenario `trials` times, `jobs` at a time. Writes results.json and summary.md to `out_dir`."""
    tasks = [(scenario, trial) for scenario in scenarios for trial in range(1, trials + 1)]
    results: list[Result] = []
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = [
            pool.submit(run_scenario, scenario, jj, out_dir / scenario.name / f"trial-{trial}", options, trial)
            for scenario, trial in tasks
        ]
        for future in as_completed(futures):
            results.append(future.result())
            on_result(results[-1], len(results), len(tasks))
    results.sort(key=lambda r: (r.scenario, r.trial))
    (out_dir / "results.json").write_text(json.dumps([asdict(r) for r in results], indent=2) + "\n")
    (out_dir / "summary.md").write_text(summarize(results))
    return results


def load_results(out_dir: Path) -> list[Result]:
    return [Result(**fields) for fields in json.loads((out_dir / "results.json").read_text())]


def summarize(results: list[Result]) -> str:
    first = results[0]
    passed = sum(r.passed for r in results)
    cost = sum(r.cost_usd or 0 for r in results)
    lines = [
        f"# jj {first.jj_version}, model {first.model}",
        "",
        f"{passed}/{len(results)} passed. Agent cost ${cost:.2f}.",
        "",
        "| Scenario | Result | Skill used | Turns | jj calls | Failed jj calls | Warnings | Editor prompts | Time |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        name = r.scenario if r.trial == 1 else f"{r.scenario} (trial {r.trial})"
        lines.append(
            f"| {name} | {'pass' if r.passed else 'FAIL'} | {'yes' if r.skill_invoked else 'no'} | {r.turns or '-'} "
            f"| {r.jj_calls} | {len(r.jj_failures)} | {len(r.warnings)} | {r.editor_prompts} | {r.duration_s:.0f}s |"
        )
    failures = [r for r in results if not r.passed]
    if failures:
        lines += ["", "## Failures", ""]
        lines += [f"- **{r.scenario}**: {r.failure} (agent finished with `{r.agent_status}`)" for r in failures]
    failed_calls = [(r.scenario, call) for r in results for call in r.jj_failures]
    if failed_calls:
        lines += ["", "## jj calls that exited non-zero", ""]
        lines += [f"- {scenario}: `jj {call}`" for scenario, call in failed_calls]
    warnings: dict[str, set[str]] = {}
    for r in results:
        for warning in r.warnings:
            warnings.setdefault(warning, set()).add(r.scenario)
    if warnings:
        lines += ["", "## Warnings jj printed", ""]
        lines += [f"- `{warning}` ({', '.join(sorted(names))})" for warning, names in warnings.items()]
    raw_git = [(r.scenario, command) for r in results for command in r.git_commands]
    if raw_git:
        lines += ["", "## Raw git commands", ""]
        lines += [f"- {scenario}: `{command.splitlines()[0]}`" for scenario, command in raw_git]
    return "\n".join(lines) + "\n"


def compare(runs: dict[str, list[Result]]) -> str:
    """One row per scenario, one column per run label."""
    labels = list(runs)
    names = sorted({r.scenario for results in runs.values() for r in results})
    lines = ["| Scenario | " + " | ".join(labels) + " |", "|---" * (len(labels) + 1) + "|"]
    for name in names:
        cells = [_cell([r for r in runs[label] if r.scenario == name]) for label in labels]
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    totals = [f"{sum(r.passed for r in runs[label])}/{len(runs[label])}" for label in labels]
    lines.append("| **passed** | " + " | ".join(totals) + " |")
    return "\n".join(lines) + "\n"


def _cell(results: list[Result]) -> str:
    if not results:
        return "-"
    passed = sum(r.passed for r in results)
    status = ("pass" if passed else "FAIL") if len(results) == 1 else f"{passed}/{len(results)} pass"
    failed_calls = sum(len(r.jj_failures) for r in results)
    if failed_calls:
        status += f" ({failed_calls} failed jj call{'' if failed_calls == 1 else 's'})"
    return status

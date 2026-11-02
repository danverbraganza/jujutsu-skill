"""Evaluate the jujutsu skill with Harbor: plain-language jj requests in real repos, graded on the end state."""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from jj_eval.repo import CheckFailure
from jj_eval.report import compare, load_trials, summarize
from jj_eval.sandbox import Sandbox
from jj_eval.scenarios import SCENARIOS
from jj_eval.tasks import write_tasks

HARBOR = ["uvx", "--from", "harbor==0.25.0", "harbor"]
SKILL_DIR = Path(__file__).resolve().parents[2] / "jujutsu"
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
DEFAULT_WORK_DIR = Path("/tmp/jj-skill-eval")
VERIFIER_LOGS = Path("/logs/verifier")
# jj exits 3 when its stdout closes early, as under `jj log -p | head`: the output was cut off, not refused.
JJ_BROKEN_PIPE = 3


def run_label(version: str, agent: str, model: str | None, skill: bool) -> str:
    label = f"jj-{version}-{agent}" + (f"-{model.replace('/', '_')}" if model else "")
    return label + ("" if skill else "-no-skill")


def check(name: str) -> None:
    """Grade the end state, writing Harbor's reward.json and the details to /logs/verifier."""
    sb = Sandbox()
    try:
        SCENARIOS[name]().check(sb)
        failure = None
    except CheckFailure as error:
        failure = str(error)
    except Exception as error:  # a mangled repo can make the check's own jj calls fail
        failure = f"check crashed: {type(error).__name__}: {error}"
    calls = sb.jj_invocations()
    failed = [call.args for call in calls if call.status not in (0, JJ_BROKEN_PIPE)]
    rewards = {
        "reward": int(failure is None),
        "jj_calls": len(calls),
        "failed_jj_calls": len(failed),
        "editor_prompts": sb.editor_invocations(),
    }
    VERIFIER_LOGS.mkdir(parents=True, exist_ok=True)
    (VERIFIER_LOGS / "reward.json").write_text(json.dumps(rewards) + "\n")
    detail = {"scenario": name, "failure": failure, "failed_jj_calls": failed}
    (VERIFIER_LOGS / "check.json").write_text(json.dumps(detail, indent=2) + "\n")
    print(failure or "pass")


def harbor_run(tasks_dir: Path, job_dir: Path, agent: str, *, trials: int, jobs: int,
               model: str | None = None, skill_dir: Path | None = None, extra: list[str] = ()) -> Path:
    shutil.rmtree(job_dir, ignore_errors=True)
    command = [*HARBOR, "run", "-p", str(tasks_dir), "-a", agent, "-k", str(trials), "-n", str(jobs),
               "-o", str(job_dir.parent), "--job-name", job_dir.name]
    if model:
        command += ["-m", model]
    if skill_dir:
        command += ["--skill", str(skill_dir)]
    if ENV_FILE.exists():
        command += ["--env-file", str(ENV_FILE)]
    subprocess.run([*command, *extra])
    return job_dir


def selftest(scenarios, version: str, work_dir: Path, jobs: int) -> list[str]:
    """Harbor's oracle agent must pass every scenario, and its do-nothing nop agent must fail every one."""
    tasks_dir = write_tasks(scenarios, version, work_dir / "tasks" / f"selftest-jj-{version}")
    problems = []
    for agent, should_pass in (("oracle", True), ("nop", False)):
        job_dir = harbor_run(tasks_dir, work_dir / "jobs" / f"selftest-jj-{version}-{agent}", agent, trials=1, jobs=jobs)
        verdicts = {trial.scenario: trial for trial in load_trials(job_dir)}
        for scenario in scenarios:
            trial = verdicts.get(scenario.name)
            if trial is None or not trial.judged:
                problems.append(f"{scenario.name}: the {agent} trial got no verdict ({trial and trial.failure})")
            elif trial.passed != should_pass:
                outcome = "passed" if trial.passed else f"failed: {trial.failure}"
                problems.append(f"{scenario.name}: {agent} should {'pass' if should_pass else 'fail'}, but {outcome}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m jj_eval", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("list", help="list the scenarios")
    for name, help in (("setup", "build the starting repo (in a task image)"),
                       ("check", "grade the end state (in a task container)"),
                       ("solve", "apply the reference solution (in a task container)")):
        commands.add_parser(name, help=help).add_argument("scenario", choices=SCENARIOS)

    def scenario_args(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("--jj-version", required=True, metavar="VERSION", help="jj release to test, e.g. 0.46.0")
        sub.add_argument("--scenario", action="append", choices=SCENARIOS, metavar="NAME", help="only this scenario")
        sub.add_argument("--tag", action="append", metavar="TAG", help="only scenarios with this tag")
        sub.add_argument("--jobs", type=int, default=4, help="trials to run at once (default: %(default)s)")
        sub.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR, help="default: %(default)s")

    tasks = commands.add_parser("tasks", help="write Harbor task directories, for running harbor yourself")
    scenario_args(tasks)
    tasks.add_argument("--out", type=Path, required=True)

    run = commands.add_parser("run", help="run an agent on the scenarios with Harbor")
    scenario_args(run)
    run.add_argument("--agent", default="claude-code", help="any Harbor agent (default: %(default)s)")
    run.add_argument("--model", help="model for the agent, e.g. anthropic/claude-sonnet-5 (default: the agent's)")
    run.add_argument("--trials", type=int, default=1, help="trials per scenario (default: %(default)s)")
    skill = run.add_mutually_exclusive_group()
    skill.add_argument("--skill-dir", type=Path, default=SKILL_DIR, help="skill to test (default: this repo's)")
    skill.add_argument("--no-skill", action="store_true", help="run without the skill, as a baseline")
    run.add_argument("harbor_args", nargs="*", help="extra `harbor run` arguments, after --")

    check_scenarios = commands.add_parser("selftest", help="check every scenario with Harbor's oracle and nop agents")
    scenario_args(check_scenarios)

    report = commands.add_parser("report", help="summarize one job, or line up several side by side")
    report.add_argument("jobs", nargs="+", type=Path, metavar="JOB_DIR")

    args = parser.parse_args(argv)

    if args.command == "list":
        for name, scenario in SCENARIOS.items():
            print(f"{name}  [{', '.join(scenario.tags)}]\n    {scenario.prompt}")
        return 0
    if args.command == "setup":
        sb = Sandbox(deterministic=True)
        sb.root.mkdir(parents=True, exist_ok=True)
        SCENARIOS[args.scenario]().setup(sb)
        return 0
    if args.command == "solve":
        SCENARIOS[args.scenario]().solve(Sandbox())
        return 0
    if args.command == "check":
        check(args.scenario)
        return 0
    if args.command == "report":
        labels = [path.name for path in args.jobs]
        if len(set(labels)) < len(labels):
            labels = [f"{path.parent.name}/{path.name}" for path in args.jobs]
        runs = {label: load_trials(path) for label, path in zip(labels, args.jobs)}
        print(summarize(labels[0], runs[labels[0]]) if len(runs) == 1 else compare(runs), end="")
        return 0

    selected = [
        scenario
        for name, scenario in SCENARIOS.items()
        if (not args.scenario or name in args.scenario) and (not args.tag or set(args.tag) & set(scenario.tags))
    ]
    if not selected:
        parser.error("no scenarios match --scenario/--tag")

    if args.command == "tasks":
        print(write_tasks(selected, args.jj_version, args.out))
        return 0
    if args.command == "selftest":
        problems = selftest(selected, args.jj_version, args.work_dir, args.jobs)
        print("\n".join(problems) if problems else f"All {len(selected)} scenarios check out on jj {args.jj_version}.")
        return 1 if problems else 0

    label = run_label(args.jj_version, args.agent, args.model, skill=not args.no_skill)
    tasks_dir = write_tasks(selected, args.jj_version, args.work_dir / "tasks" / label)
    job_dir = harbor_run(
        tasks_dir, args.work_dir / "jobs" / label, args.agent, trials=args.trials, jobs=args.jobs,
        model=args.model, skill_dir=None if args.no_skill else args.skill_dir.resolve(), extra=args.harbor_args,
    )
    if not (job_dir / "result.json").exists():
        print(f"harbor wrote no results to {job_dir}; see its output above", file=sys.stderr)
        return 1
    trials = load_trials(job_dir)
    summary = summarize(label, trials)
    (job_dir / "summary.md").write_text(summary)
    print(summary, end="")
    return 0 if trials and all(trial.passed for trial in trials) else 1


if __name__ == "__main__":
    sys.exit(main())

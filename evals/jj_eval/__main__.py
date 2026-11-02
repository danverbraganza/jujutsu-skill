"""Evaluate the jujutsu skill: ask Claude Code for jj outcomes in plain language, then check the repo."""

import argparse
import sys
from pathlib import Path

from jj_eval.binaries import ensure_jj, jj_version
from jj_eval.runner import SKILL_DIR, Options, compare, load_results, run_all, summarize
from jj_eval.scenarios import SCENARIOS

DEFAULT_WORK_DIR = Path("/tmp/jj-skill-eval")


def run_label(version: str, model: str, skill: bool) -> str:
    return f"jj-{version}-{model}" + ("" if skill else "-no-skill")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m jj_eval", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("list", help="list the scenarios")

    fetch = commands.add_parser("fetch", help="download jj release binaries into the cache")
    fetch.add_argument("versions", nargs="+", metavar="VERSION")

    run = commands.add_parser("run", help="run scenarios with Claude Code against one jj version")
    jj = run.add_mutually_exclusive_group(required=True)
    jj.add_argument("--jj-version", metavar="VERSION", help="jj release to download and test, e.g. 0.46.0")
    jj.add_argument("--jj", type=Path, metavar="PATH", help="test this jj binary instead of a release")
    run.add_argument("--model", default="sonnet", help="model for the agent (default: %(default)s)")
    run.add_argument("--scenario", action="append", choices=SCENARIOS, metavar="NAME", help="only this scenario")
    run.add_argument("--tag", action="append", metavar="TAG", help="only scenarios with this tag")
    run.add_argument("--trials", type=int, default=1, help="runs per scenario (default: %(default)s)")
    run.add_argument("--jobs", type=int, default=4, help="agents to run at once (default: %(default)s)")
    run.add_argument("--max-turns", type=int, default=40, help="agent turn limit (default: %(default)s)")
    run.add_argument("--timeout", type=float, default=900, help="seconds per agent run (default: %(default)s)")
    run.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR, help="default: %(default)s")
    skill = run.add_mutually_exclusive_group()
    skill.add_argument("--skill-dir", type=Path, default=SKILL_DIR, help="skill to test (default: this repo's)")
    skill.add_argument("--no-skill", action="store_true", help="run without any jj skill, as a baseline")
    run.add_argument("--claude", default="claude", help="Claude Code executable (default: %(default)s)")

    comparison = commands.add_parser("compare", help="line up finished runs side by side")
    comparison.add_argument("runs", nargs="+", type=Path, metavar="RUN_DIR", help="directory holding results.json")

    args = parser.parse_args(argv)

    if args.command == "list":
        for name, scenario in SCENARIOS.items():
            print(f"{name}  [{', '.join(scenario.tags)}]\n    {scenario.prompt}")
        return 0

    if args.command == "fetch":
        for version in args.versions:
            print(ensure_jj(version))
        return 0

    if args.command == "compare":
        labels = [path.name for path in args.runs]
        if len(set(labels)) < len(labels):  # e.g. one jj version before and after a skill change
            labels = [f"{path.parent.name}/{path.name}" for path in args.runs]
        print(compare({label: load_results(path) for label, path in zip(labels, args.runs)}), end="")
        return 0

    binary = args.jj.resolve() if args.jj else ensure_jj(args.jj_version)
    version = jj_version(binary)
    selected = [
        scenario
        for name, scenario in SCENARIOS.items()
        if (not args.scenario or name in args.scenario) and (not args.tag or set(args.tag) & set(scenario.tags))
    ]
    if not selected:
        parser.error("no scenarios match --scenario/--tag")
    options = Options(
        model=args.model,
        max_turns=args.max_turns,
        timeout=args.timeout,
        skill_dir=None if args.no_skill else args.skill_dir.resolve(),
        claude=args.claude,
    )
    out_dir = args.work_dir / run_label(version, args.model, skill=not args.no_skill)
    print(f"jj {version} ({binary}), model {args.model}, {len(selected)} scenarios -> {out_dir}", flush=True)

    def report(result, done, total):
        status = "pass" if result.passed else "FAIL"
        print(f"[{done:>2}/{total}] {status}  {result.scenario}  ({result.duration_s:.0f}s)", flush=True)
        if result.failure:
            print(f"        {result.failure}", flush=True)

    results = run_all(selected, binary, out_dir, options, trials=args.trials, jobs=args.jobs, on_result=report)
    print()
    print(summarize(results), end="")
    print(f"\nSummary written to {out_dir / 'summary.md'}")
    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())

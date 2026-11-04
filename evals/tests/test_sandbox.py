from jj_eval.sandbox import Sandbox


def test_scenario_repos_are_created_and_cloned_without_colocation(tmp_path):
    jj = tmp_path / "jj"
    jj.write_text('#!/bin/sh\necho "$@" >> "$(dirname "$0")/jj-args.log"\n')
    jj.chmod(0o755)
    sb = Sandbox(root=tmp_path / "app", jj=jj)
    sb.root.mkdir()

    sb.init_repo()
    sb.clone_origin()

    assert (tmp_path / "jj-args.log").read_text().splitlines() == [
        "git init --no-colocate",
        f"git clone --no-colocate {sb.origin_dir} repo",
    ]

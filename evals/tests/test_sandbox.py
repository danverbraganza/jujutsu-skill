import json
import subprocess


def agent_jj(sandbox, *args):
    return subprocess.run(
        ["jj", *args], cwd=sandbox.repo_dir, env=sandbox.agent_env(), capture_output=True, text=True, timeout=60
    )


def test_agent_jj_calls_go_through_the_logging_shim(sandbox):
    sandbox.init_repo()
    agent_jj(sandbox, "st")
    agent_jj(sandbox, "no-such-command")

    invocations = sandbox.jj_invocations()
    assert [i.args for i in invocations] == ["st", "no-such-command"]
    assert invocations[0].status == 0 and invocations[1].status != 0


def test_editor_prompts_fail_fast_and_are_counted(sandbox):
    sandbox.init_repo()
    result = agent_jj(sandbox, "describe")

    assert result.returncode != 0
    assert sandbox.editor_invocations() == 1


def test_agent_env_drops_the_parent_session_but_keeps_auth(sandbox, monkeypatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "parent")
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "token")
    monkeypatch.setenv("JJ_USER", "someone else")
    env = sandbox.agent_env()

    assert "CLAUDECODE" not in env and "CLAUDE_CODE_SESSION_ID" not in env and "JJ_USER" not in env
    assert env["CLAUDE_CODE_OAUTH_TOKEN"] == "token"
    assert env["PATH"].startswith(str(sandbox.bin_dir))


def test_install_skill_packages_a_plugin(sandbox, tmp_path):
    skill = tmp_path / "jujutsu"
    skill.mkdir()
    (skill / "SKILL.md").write_text("---\nname: jujutsu\n---\n")
    plugin = sandbox.install_skill(skill)

    assert (plugin / "skills" / "jujutsu" / "SKILL.md").read_text().startswith("---")
    assert json.loads((plugin / ".claude-plugin" / "plugin.json").read_text())["name"] == "jujutsu"

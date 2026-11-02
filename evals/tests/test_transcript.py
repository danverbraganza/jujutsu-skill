import json

from jj_eval.agent import Transcript


def events():
    yield {"type": "system", "subtype": "init", "skills": ["jujutsu:jujutsu"], "model": "claude-sonnet-5"}
    yield assistant(tool_use("t1", "Skill", {"skill": "jujutsu:jujutsu"}))
    yield tool_result("t1", "Launching skill: jujutsu")
    yield assistant(tool_use("t2", "Bash", {"command": "jj describe --author 'A <a@example.com>' -m x"}))
    yield tool_result(
        "t2",
        [{"type": "text", "text": "Warning: `jj describe --author` is deprecated\nWorking copy now at: abc"}],
    )
    yield assistant(tool_use("t3", "Bash", {"command": "cd repo && git status"}))
    yield tool_result("t3", "fatal: not a git repository", is_error=True)
    yield assistant(tool_use("t4", "Bash", {"command": "jj git push -b main"}))
    yield tool_result("t4", "Warning: `jj describe --author` is deprecated\nPushed")
    yield {"type": "result", "subtype": "success", "num_turns": 4, "total_cost_usd": 0.25, "result": "Done."}


def assistant(*content):
    return {"type": "assistant", "message": {"content": list(content)}}


def tool_use(tool_id, name, tool_input):
    return {"type": "tool_use", "id": tool_id, "name": name, "input": tool_input}


def tool_result(tool_id, content, is_error=False):
    block = {"type": "tool_result", "tool_use_id": tool_id, "content": content, "is_error": is_error}
    return {"type": "user", "message": {"content": [block]}}


def test_parse_pairs_tool_calls_with_their_results():
    transcript = Transcript.parse(json.dumps(event) for event in events())

    commands = [call.input["command"] for call in transcript.bash_calls]
    assert commands == [
        "jj describe --author 'A <a@example.com>' -m x",
        "cd repo && git status",
        "jj git push -b main",
    ]
    assert transcript.bash_calls[1].is_error
    assert transcript.bash_calls[0].output.startswith("Warning:")
    assert transcript.skill_invoked
    assert transcript.result["num_turns"] == 4


def test_diagnostics_extract_warnings_and_raw_git_use():
    transcript = Transcript.parse(json.dumps(event) for event in events())

    assert transcript.warnings() == ["Warning: `jj describe --author` is deprecated"]
    assert transcript.git_commands() == ["cd repo && git status"]


def test_parse_tolerates_a_truncated_stream():
    lines = [json.dumps(event) for event in events()][:4] + ['{"type": "assist']
    transcript = Transcript.parse(lines)

    assert transcript.result is None
    assert transcript.bash_calls[0].output == ""

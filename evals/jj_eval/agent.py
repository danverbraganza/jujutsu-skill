"""Run Claude Code headlessly in a sandbox and parse its stream-json transcript."""

import json
import os
import re
import signal
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping

# A shell segment that starts with `git` (so `jj git push` does not count).
RAW_GIT = re.compile(r"(?:^|[;&|(\n]\s*)git\s")


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict
    output: str = ""
    is_error: bool = False


@dataclass
class Transcript:
    init: dict | None = None
    result: dict | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)

    @classmethod
    def parse(cls, lines: Iterable[str]) -> "Transcript":
        transcript = cls()
        calls: dict[str, ToolCall] = {}
        for line in lines:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue  # a killed run can end mid-line
            kind = event.get("type")
            if kind == "system" and event.get("subtype") == "init":
                transcript.init = event
            elif kind == "result":
                transcript.result = event
            elif kind in ("assistant", "user"):
                content = event.get("message", {}).get("content", [])
                for block in content if isinstance(content, list) else []:
                    if block.get("type") == "tool_use":
                        call = ToolCall(block["id"], block["name"], block.get("input", {}))
                        calls[call.id] = call
                        transcript.tool_calls.append(call)
                    elif block.get("type") == "tool_result" and block.get("tool_use_id") in calls:
                        call = calls[block["tool_use_id"]]
                        call.output = _text(block.get("content"))
                        call.is_error = bool(block.get("is_error"))
        return transcript

    @property
    def bash_calls(self) -> list[ToolCall]:
        return [call for call in self.tool_calls if call.name == "Bash"]

    @property
    def skill_invoked(self) -> bool:
        return any(call.name == "Skill" and "jujutsu" in json.dumps(call.input) for call in self.tool_calls)

    def warnings(self) -> list[str]:
        """Distinct `Warning:` lines that jj printed to the agent, in first-seen order."""
        seen: dict[str, None] = {}
        for call in self.bash_calls:
            for line in call.output.splitlines():
                if line.startswith("Warning:"):
                    seen.setdefault(line.strip(), None)
        return list(seen)

    def git_commands(self) -> list[str]:
        """Bash commands where the agent reached for raw git instead of jj."""
        return [call.input.get("command", "") for call in self.bash_calls if RAW_GIT.search(call.input.get("command", ""))]


def _text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return ""


@dataclass
class AgentRun:
    transcript: Transcript
    exit_code: int | None
    timed_out: bool
    duration_s: float


def run_claude(
    prompt: str,
    *,
    cwd: Path,
    env: Mapping[str, str],
    plugin_dir: Path | None,
    model: str,
    max_turns: int,
    timeout: float,
    transcript_path: Path,
    claude: str = "claude",
) -> AgentRun:
    command = [
        claude,
        "-p",
        prompt,
        "--model",
        model,
        "--output-format",
        "stream-json",
        "--verbose",
        # Load only the skill under test: no user CLAUDE.md, skills, plugins, hooks, or MCP servers.
        "--setting-sources",
        "project,local",
        "--strict-mcp-config",
        "--settings",
        json.dumps({"autoMemoryEnabled": False}),
        "--permission-mode",
        "bypassPermissions",
        "--no-session-persistence",
        "--max-turns",
        str(max_turns),
    ]
    if plugin_dir is not None:
        command += ["--plugin-dir", str(plugin_dir)]
    start = time.monotonic()
    stderr_path = transcript_path.with_name("claude-stderr.log")
    with transcript_path.open("w") as stdout, stderr_path.open("w") as stderr:
        process = subprocess.Popen(
            command, cwd=cwd, env=dict(env), stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
            start_new_session=True,
        )
        try:
            exit_code: int | None = process.wait(timeout=timeout)
            timed_out = False
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            exit_code, timed_out = None, True
    transcript = Transcript.parse(transcript_path.read_text().splitlines())
    return AgentRun(transcript, exit_code, timed_out, time.monotonic() - start)

help: 
    @just --list

install: 
    cp -r ./jujutsu/ ~/.claude/skills/jujutsu

# Validate every eval scenario against real jj binaries (no agent, no API calls)
eval-selftest:
    cd evals && uv run pytest

# Run the agent eval against a jj release, e.g. `just eval 0.46.0 --model opus`
eval version *args:
    cd evals && uv run python -m jj_eval run --jj-version {{version}} {{args}}

# Line up finished eval runs side by side
eval-compare +run_dirs:
    cd evals && uv run python -m jj_eval compare {{run_dirs}}

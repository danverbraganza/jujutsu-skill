help: 
    @just --list

install: 
    cp -r ./jujutsu/ ~/.claude/skills/jujutsu

# Check every eval scenario with Harbor's oracle (must pass) and nop (must fail) agents; Docker only, no API calls
eval-selftest version="0.47.1":
    cd evals && uv run python -m jj_eval selftest --jj-version {{version}}

# Run an agent on the eval scenarios with Harbor, e.g. `just eval 0.47.1 --agent pi --trials 3`
eval version *args:
    cd evals && uv run python -m jj_eval run --jj-version {{version}} {{args}}

# Summarize a finished eval job, or line up several side by side
eval-report +job_dirs:
    cd evals && uv run python -m jj_eval report {{job_dirs}}

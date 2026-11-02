import re

import pytest

from jj_eval.repo import CheckFailure
from jj_eval.sandbox import Sandbox
from jj_eval.scenarios import SCENARIOS


@pytest.mark.parametrize("name", SCENARIOS)
def test_check_rejects_the_setup_and_accepts_the_reference_solution(name, jj, tmp_path):
    scenario = SCENARIOS[name]()
    sandbox = Sandbox.create(tmp_path / name, jj)
    scenario.setup(sandbox)

    with pytest.raises(CheckFailure):
        scenario.check(sandbox)

    scenario.solve(sandbox)
    scenario.check(sandbox)


@pytest.mark.parametrize("name", SCENARIOS)
def test_prompt_is_plain_language(name):
    prompt = SCENARIOS[name].prompt
    assert not re.search(r"\bjj\b", prompt), "prompts describe the goal; they never name jj commands"

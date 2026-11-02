from jj_eval.__main__ import main, run_label
from jj_eval.scenarios import SCENARIOS


def test_list_prints_every_scenario_with_its_prompt(capsys):
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    for name, scenario in SCENARIOS.items():
        assert name in out and scenario.prompt in out


def test_run_label_names_the_jj_version_model_and_skill():
    assert run_label("0.46.0", "sonnet", skill=True) == "jj-0.46.0-sonnet"
    assert run_label("0.37.0", "opus", skill=False) == "jj-0.37.0-opus-no-skill"

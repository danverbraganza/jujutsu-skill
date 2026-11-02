"""Every scenario, keyed by name. Importing a module registers the scenarios it defines."""

from jj_eval.scenario import REGISTRY
from jj_eval.scenarios import everyday, rewriting  # noqa: F401

SCENARIOS = dict(sorted(REGISTRY.items()))

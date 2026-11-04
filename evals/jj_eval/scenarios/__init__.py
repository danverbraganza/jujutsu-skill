"""Every scenario, keyed by name. Importing a module registers the scenarios it defines."""

from jj_eval.scenario import REGISTRY
from jj_eval.scenarios import edge_cases, everyday, interop, remotes, rewriting  # noqa: F401

SCENARIOS = dict(sorted(REGISTRY.items()))

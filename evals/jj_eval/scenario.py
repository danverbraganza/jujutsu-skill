"""The scenario contract: build a repo, ask for an outcome in plain language, check only the end state."""

from typing import ClassVar

from jj_eval.sandbox import Sandbox

REGISTRY: dict[str, type["Scenario"]] = {}


class Scenario:
    name: ClassVar[str]
    prompt: ClassVar[str]
    tags: ClassVar[tuple[str, ...]] = ()

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if cls.name in REGISTRY:
            raise ValueError(f"duplicate scenario name {cls.name!r}")
        REGISTRY[cls.name] = cls

    def setup(self, sb: Sandbox) -> None:
        """Build the starting repo in `sb`. Runs with pinned seeds and timestamps, so it is reproducible."""
        raise NotImplementedError

    def check(self, sb: Sandbox) -> None:
        """Raise CheckFailure unless the repo is in the state the prompt asked for, however it got there."""
        raise NotImplementedError

    def solve(self, sb: Sandbox) -> None:
        """A reference solution. The self-test runs it to prove `check` can pass; agents never see it."""
        raise NotImplementedError

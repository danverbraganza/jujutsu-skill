import os

import pytest

from jj_eval.binaries import ensure_jj
from jj_eval.sandbox import Sandbox

VERSIONS = os.environ.get("JJ_EVAL_VERSIONS", "0.37.0,0.46.0").split(",")


@pytest.fixture(scope="session", params=VERSIONS, ids=lambda v: f"jj-{v}")
def jj(request):
    return ensure_jj(request.param)


@pytest.fixture
def sandbox(tmp_path, jj):
    return Sandbox.create(tmp_path / "sandbox", jj)

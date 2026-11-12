import re

import parlrag


def test_package_exposes_version() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+.*", parlrag.__version__)

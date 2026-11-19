import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "module",
    [
        "app.celery.tasks",
        "app.services.post_service",
        "app.services.comment_service",
        "app.services.moderation",
    ],
)
def test_module_imports_first_in_a_fresh_interpreter(module: str):
    result = subprocess.run(
        [sys.executable, "-c", f"import {module}"], capture_output=True, text=True
    )

    assert result.returncode == 0, result.stderr

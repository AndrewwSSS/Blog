import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "module",
    [
        "app.celery.app",
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


def test_celery_app_does_not_import_the_tasks():
    code = "import sys, app.celery.app; assert 'app.celery.tasks' not in sys.modules"
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr


def test_worker_registers_every_task_from_the_celery_app():
    from app.celery.app import celery

    celery.loader.import_default_modules()

    assert {"outbox.publish_pending", "outbox.delete_old_published"} <= set(celery.tasks)
    assert "app.celery.tasks.create_reply_for_post" in celery.tasks

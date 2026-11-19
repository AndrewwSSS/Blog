from pathlib import Path

from app.core.config import Settings

ENV_TEMPLATE = Path(__file__).resolve().parent.parent / ".env.template"

OPTIONAL_WITH_DEFAULTS = {
    "POSTGRES_PORT": 5432,
    "REDIS_PORT": 6379,
    "ACCESS_TOKEN_EXPIRE_MINUTES": 30,
    "EMAIL_TOKEN_EXPIRE_HOURS": 24,
}


def test_env_template_with_empty_optional_values_loads(required_env, monkeypatch):
    for name in OPTIONAL_WITH_DEFAULTS:
        monkeypatch.delenv(name, raising=False)

    loaded = Settings(_env_file=ENV_TEMPLATE)

    for name, default in OPTIONAL_WITH_DEFAULTS.items():
        assert getattr(loaded, name) == default


def test_database_url_uses_configured_port(required_env):
    loaded = Settings(_env_file=None, POSTGRES_PORT=6543)

    assert loaded.database_url == "postgresql+asyncpg://user:password@db:6543/blog"

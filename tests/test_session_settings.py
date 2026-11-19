from app.db.session import async_session
from tests.fixtures import async_session_maker


def without_bind(options: dict) -> dict:
    return {name: value for name, value in options.items() if name != "bind"}


def test_tests_use_production_session_settings():
    assert without_bind(async_session_maker.kw) == without_bind(async_session.kw)
    assert async_session_maker.class_ is async_session.class_


def test_sessions_do_not_autoflush_or_expire_on_commit():
    assert async_session.kw["autoflush"] is False
    assert async_session.kw["expire_on_commit"] is False

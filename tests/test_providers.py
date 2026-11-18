import pytest
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.core.reply_generators import get_reply_generator
from app.core.reply_generators.groq_reply_generator import GroqReplyGenerator
from app.core.validation import get_content_validator
from app.core.validation.groq_validator import GroqValidator
from app.core.validation.openai_validator import OpenContentValidator


def test_default_providers_are_groq():
    assert isinstance(get_content_validator(), GroqValidator)
    assert isinstance(get_reply_generator(), GroqReplyGenerator)


def test_content_validator_can_be_switched_to_openai(monkeypatch):
    monkeypatch.setattr(settings, "CONTENT_VALIDATOR", "openai")

    assert isinstance(get_content_validator(), OpenContentValidator)


def test_content_validator_is_read_from_env(required_env, monkeypatch):
    monkeypatch.setenv("CONTENT_VALIDATOR", "openai")

    assert Settings(_env_file=None).CONTENT_VALIDATOR == "openai"


def test_unknown_provider_is_rejected_at_startup(required_env, monkeypatch):
    monkeypatch.setenv("CONTENT_VALIDATOR", "chatbot-9000")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)

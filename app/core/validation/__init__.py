from app.core.config import settings
from app.core.validation.base_content_validator import BaseContentValidator
from app.core.validation.groq_validator import GroqValidator
from app.core.validation.openai_validator import OpenContentValidator

CONTENT_VALIDATORS: dict[str, type[BaseContentValidator]] = {
    "groq": GroqValidator,
    "openai": OpenContentValidator,
}


def get_content_validator() -> BaseContentValidator:
    """Return the content validator selected by settings.CONTENT_VALIDATOR."""
    return CONTENT_VALIDATORS[settings.CONTENT_VALIDATOR]()

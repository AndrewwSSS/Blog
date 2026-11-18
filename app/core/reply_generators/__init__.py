from app.core.config import settings
from app.core.reply_generators.base_ai_reply_generator import BaseAIReplyGenerator
from app.core.reply_generators.groq_reply_generator import GroqReplyGenerator

REPLY_GENERATORS: dict[str, type[BaseAIReplyGenerator]] = {
    "groq": GroqReplyGenerator,
}


def get_reply_generator() -> BaseAIReplyGenerator:
    """Return the reply generator selected by settings.REPLY_GENERATOR."""
    return REPLY_GENERATORS[settings.REPLY_GENERATOR]()

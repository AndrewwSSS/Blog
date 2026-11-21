import logging
import re

_VERIFICATION_TOKEN = re.compile(r"(/verification/)(?!resend(?:[/?]|$))[^/?\s]+")


def mask_verification_token(path: str) -> str:
    """Replace the token in a verification link path with ***."""
    return _VERIFICATION_TOKEN.sub(r"\1***", path)


class MaskVerificationTokenFilter(logging.Filter):
    """Hide email verification tokens in log record arguments, e.g. uvicorn access lines."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple):
            record.args = tuple(
                mask_verification_token(arg) if isinstance(arg, str) else arg for arg in record.args
            )
        return True

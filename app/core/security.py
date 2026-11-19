import re

import bcrypt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from app.core.config import settings

# Argon2id with the argon2-cffi defaults (RFC 9106 low-memory profile: 64 MiB, t=3, p=4).
password_hasher = PasswordHasher()

# Legacy bcrypt hashes from passlib used only the first 72 bytes of the password.
BCRYPT_MAX_PASSWORD_BYTES = 72
BCRYPT_PREFIXES = ("$2a$", "$2b$", "$2y$")
# bcrypt panics on malformed input, so the full format is checked before calling it.
BCRYPT_HASH_FORMAT = re.compile(r"\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}")

serializer = URLSafeTimedSerializer(settings.SECRET_KEY)


def generate_email_verification_token(email: str) -> str:
    return serializer.dumps(email, salt=settings.EMAIL_TOKEN_SALT)


def verify_verification_token(token: str) -> str | None:
    try:
        email = serializer.loads(
            token,
            salt=settings.EMAIL_TOKEN_SALT,
            max_age=settings.EMAIL_TOKEN_EXPIRE_HOURS * 3600,
        )
        return email
    except (BadSignature, SignatureExpired):
        return None


def _is_bcrypt(hashed_password: str) -> bool:
    return hashed_password.startswith(BCRYPT_PREFIXES)


def _verify_bcrypt(plain_password: str, hashed_password: str) -> bool:
    if not BCRYPT_HASH_FORMAT.fullmatch(hashed_password):
        return False
    password = plain_password.encode("utf-8")[:BCRYPT_MAX_PASSWORD_BYTES]
    try:
        return bcrypt.checkpw(password, hashed_password.encode("ascii"))
    except ValueError:
        return False


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a password against an Argon2id hash or a legacy bcrypt hash.

    A malformed hash never matches.
    """
    if _is_bcrypt(hashed_password):
        return _verify_bcrypt(plain_password, hashed_password)
    try:
        return password_hasher.verify(hashed_password, plain_password)
    except (VerificationError, InvalidHashError):
        return False


def password_needs_rehash(hashed_password: str) -> bool:
    """Return True for a verified hash that should be replaced with a current Argon2id hash."""
    return _is_bcrypt(hashed_password) or password_hasher.check_needs_rehash(hashed_password)


def get_password_hash(password: str) -> str:
    return password_hasher.hash(password)


# Made at import, so the first unknown-user login is not slower than the others.
_DUMMY_HASH = get_password_hash("dummy-password")


def dummy_verify_password() -> None:
    """Spend the same time as verify_password, to hide whether a user exists."""
    verify_password("not-the-dummy-password", _DUMMY_HASH)

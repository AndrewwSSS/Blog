from passlib.context import CryptContext
from itsdangerous import (
    URLSafeTimedSerializer,
    BadSignature,
    SignatureExpired
)

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
serializer = URLSafeTimedSerializer(settings.SECRET_KEY)


def generate_email_verification_token(email: str) -> str:
    return serializer.dumps(email, salt=settings.EMAIL_TOKEN_SALT)


def verify_verification_token(token: str) -> str | None:
    try:
        email = serializer.loads(
            token,
            salt=settings.EMAIL_TOKEN_SALT,
        )
        return email
    except (BadSignature, SignatureExpired):
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

import jwt
from datetime import datetime, timedelta
from app.core.config import settings


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    to_encode.update({"token_type": "access"})
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    to_encode.update({"token_type": "refresh"})
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("user_id")
        token_type: str = payload.get("token_type")

        if not user_id or not isinstance(user_id, int):
            raise jwt.InvalidTokenError("Invalid token")
        if not token_type or token_type not in settings.TOKEN_TYPES:
            raise jwt.InvalidTokenError("Invalid token type")

        return payload
    except jwt.ExpiredSignatureError:
        raise jwt.InvalidTokenError("Token has expired")
    except jwt.InvalidTokenError:
        raise jwt.InvalidTokenError("Invalid token")

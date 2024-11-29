from fastapi import HTTPException, status
from jwt import InvalidTokenError
import json

from sqlalchemy.exc import IntegrityError

from app.core.auth.utils import create_access_token
from app.core.auth.utils import create_refresh_token
from app.core.auth.utils import verify_token
from app.core.security import verify_password
from app.repositories.user_repository import UserRepository
from app.schemas.jwt import LoginResponse, TokenRefreshResponse
from app.schemas.user import UserRegister, UserLoginRequest
from app.schemas.user import UserInDB
from app.schemas.user import UserRead
from app.schemas.user import UserUpdate
from app.pubsub.async_kafka_producer import AsyncKafkaProducer
from app.core.security import (
    verify_verification_token,
    generate_email_verification_token
)


class UserService:
    def __init__(self, user_repository: UserRepository):
        self.repository = user_repository

    async def create_user(self, user: UserRegister) -> UserInDB:
        try:
            created_user = await self.repository.create(user)
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this username or email already exists."
            )
        verification_token = generate_email_verification_token(
            created_user.email,
        )
        payload = json.dumps(
            {
                "id": created_user.id,
                "verification_url": f"http://127.0.0.1:8000/api/v1/"
                                    f"users/verification/{verification_token}",
            }
        )
        await AsyncKafkaProducer.publish(
            "new-user-registration",
            payload,
        )
        return created_user

    async def read_users(self) -> [UserRead]:
        return await self.repository.get_list()

    async def get_user_by_id(self, user_id: int) -> UserInDB:
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found",
            )
        return user

    async def authenticate_user(self, user: UserLoginRequest) -> UserInDB:
        user_db = await self.repository.get_by_username(
            user.username
        )
        if not user_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        if not verify_password(user.password, user_db.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )

        if not user_db.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user, verify you account",
            )

        return user_db

    async def login_user(self, user: UserLoginRequest) -> LoginResponse:
        user = await self.authenticate_user(user)

        access_token = create_access_token(
            data={"user_id": user.id},
        )
        refresh_token = create_refresh_token(
            data={"user_id": user.id},
        )

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token
        )

    async def refresh_access_token(self, refresh_token: str) -> TokenRefreshResponse:
        try:
            payload = verify_token(refresh_token)
        except InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if payload["token_type"] != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = await self.get_user_by_id(payload["user_id"])

        new_access_token = create_access_token(
            data={"user_id": user.id},
        )
        return TokenRefreshResponse(
            access_token=new_access_token,
        )

    async def update_by_id(self, user_id: int, user: UserUpdate) -> UserInDB:
        return await self.repository.update_by_id(
            user_id=user_id,
            fields=user.dict()
        )

    async def verify_user(
        self,
        token: str,
    ):
        email = verify_verification_token(
            token=token
        )

        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        user = await self.repository.get_by_email(email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        if user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already active"
            )

        await self.repository.update_by_id(
            user_id=user.id,
            fields={"is_active": True}
        )
        await AsyncKafkaProducer.publish(
            topic="new-active-user",
            data=json.dumps({"email": email})
        )

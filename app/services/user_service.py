from fastapi import HTTPException, status
from jwt import InvalidTokenError

from app.core.auth.utils import create_access_token
from app.core.auth.utils import create_refresh_token
from app.core.auth.utils import verify_token
from app.core.security import verify_password
from app.repositories.user_repository import UserRepository
from app.schemas.user import User
from app.schemas.user import UserInDB
from app.schemas.user import UserRead


class UserService:
    def __init__(self, user_repository: UserRepository):
        self.repository = user_repository

    async def create_user(self, user: User) -> UserRead:
        return await self.repository.create_user(user)

    async def read_users(self) -> [UserRead]:
        return await self.repository.get_users()

    async def get_user_by_id(self, user_id: int) -> UserRead:
        user = await self.repository.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found",
            )
        return user

    async def authenticate_user(self, user: User) -> UserInDB:
        user_db = await self.repository.get_user_by_username(
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
        return user_db

    async def get_jwt_tokens(self, user: User) -> dict:
        user = await self.authenticate_user(user)

        access_token = create_access_token(
            data={"user_id": user.id},
        )
        refresh_token = create_refresh_token(
            data={"user_id": user.id},
        )
        return {"access_token": access_token, "refresh_token": refresh_token}

    async def refresh_access_token(self, refresh_token: str) -> dict:
        try:
            user_id = verify_token(refresh_token)
        except InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = await self.get_user_by_id(user_id)

        new_access_token = create_access_token(
            data={"user_id": user.id},
        )
        return {"access_token": new_access_token}


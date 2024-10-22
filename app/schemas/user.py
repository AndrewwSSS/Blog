from pydantic import BaseModel, EmailStr, validator
from pydantic import field_validator


class User(BaseModel):
    username: str
    email: EmailStr | None = None
    password: str

    class Config:
        from_attributes = True


class UserRead(BaseModel):
    id: int
    post_auto_reply: bool
    reply_after: float
    username: str
    email: EmailStr | None = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    post_auto_reply: bool | None = None
    reply_after: float | None = None

    @field_validator("reply_after")
    def check_reply_after(cls, value) -> float:
        if value and value < 1:
            raise ValueError("reply_after must be greater than 1(second)")
        return value


class UserInDB(BaseModel):
    id: int
    username: str
    email: EmailStr | None = None
    post_auto_reply: bool
    reply_after: float
    hashed_password: str

    class Config:
        from_attributes = True

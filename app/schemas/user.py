from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    username: str
    email: EmailStr | None = None
    password: str


class UserRead(BaseModel):
    id: int
    post_auto_reply: bool
    reply_after: float
    username: str
    email: EmailStr | None = None

    class Config:
        from_attributes = True


class UserUpdate(UserCreate):
    username: str | None = None
    email: EmailStr | None = None
    password: str | None = None
    post_auto_reply: bool | None = None
    reply_after: float | None = None

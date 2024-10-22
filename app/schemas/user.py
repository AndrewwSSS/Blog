from pydantic import BaseModel, EmailStr


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


class UserInDB(BaseModel):
    id: int
    username: str
    email: EmailStr | None = None
    post_auto_reply: bool
    reply_after: float
    hashed_password: str

    class Config:
        from_attributes = True

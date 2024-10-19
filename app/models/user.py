from sqlalchemy import Column, Integer, String, Boolean, Float
from sqlalchemy.orm import relationship
from app.db.base_model import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    email = Column(String, unique=True, nullable=True)
    hashed_password = Column(String)
    post_auto_reply = Column(Boolean, default=False)
    reply_after = Column(Float, default=1)

    posts = relationship("Post", back_populates="owner")
    comments = relationship("Comment", back_populates="owner")

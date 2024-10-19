from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime
)
from sqlalchemy.orm import relationship
from app.db.base_model import BaseModel


class Comment(BaseModel):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True)
    content = Column(String)
    owner_id = Column(Integer, ForeignKey("users.id"))
    post_id = Column(Integer, ForeignKey("posts.id"))
    date_posted = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="comments")
    post = relationship("Post", back_populates="comments")

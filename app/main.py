from fastapi import FastAPI
from app.api.v1.endpoints import user, posts, comments

app = FastAPI()

app.include_router(user.router, prefix="/api/v1/users", tags=["user"])
app.include_router(posts.router, prefix="/api/v1/posts", tags=["posts"])
app.include_router(comments.router, prefix="/api/v1/comments", tags=["comments"])

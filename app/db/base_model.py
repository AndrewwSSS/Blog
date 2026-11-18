from sqlalchemy.orm import declarative_base


BaseModel = declarative_base()


# Registers all models on BaseModel.metadata (used by Alembic and tests).
from app.models import *  # noqa: E402, F403

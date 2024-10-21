from app.repositories.comment_repository import CommentRepository


class CommentService:
    def __init__(self, comment_repository: CommentRepository) -> None:
        self.repository = comment_repository

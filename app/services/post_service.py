from app.repositories.post_repository import PostRepository


class PostService:
    def __init__(self, post_repository: PostRepository) -> None:
        self.repository = post_repository

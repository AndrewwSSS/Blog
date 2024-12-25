class PagePaginator:
    def __init__(
        self,
        page: int,
        limit: int,
        total_records: int,
    ):
        self.page = page
        self.limit = limit
        self.total_records = total_records

    @property
    def total_pages(self) -> int:
        return (self.total_records + self.limit - 1) // self.limit

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit

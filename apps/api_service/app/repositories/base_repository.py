from sqlalchemy.orm import Query


DEFAULT_LIMIT = 100
MAX_LIMIT = 500


class BaseRepository:
    def normalize_pagination(
        self,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> tuple[int, int]:
        normalized_limit = min(max(limit, 1), MAX_LIMIT)
        normalized_offset = max(offset, 0)
        return normalized_limit, normalized_offset

    def paginate(self, query: Query, limit: int = DEFAULT_LIMIT, offset: int = 0) -> Query:
        normalized_limit, normalized_offset = self.normalize_pagination(limit, offset)
        return query.offset(normalized_offset).limit(normalized_limit)

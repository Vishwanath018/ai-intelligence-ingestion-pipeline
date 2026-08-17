from datetime import datetime, timedelta, timezone

from src.freshness.date_parser import DateParser


class FreshnessValidator:

    def __init__(self, max_age_hours: int = 24):
        self.max_age = timedelta(hours=max_age_hours)

    def is_fresh(
        self,
        published_value: str | datetime | None,
        now: datetime | None = None,
    ) -> bool:

        if published_value is None:
            return False

        if now is None:
            now = datetime.now(timezone.utc)

        if isinstance(published_value, str):
            published_at = DateParser.parse_date(
                published_value
            )
        else:
            published_at = published_value

        if published_at is None:
            return False

        if published_at.tzinfo is None:
            published_at = published_at.replace(
                tzinfo=timezone.utc
            )

        published_at = published_at.astimezone(
            timezone.utc
        )

        age = now - published_at

        return timedelta(0) <= age <= self.max_age
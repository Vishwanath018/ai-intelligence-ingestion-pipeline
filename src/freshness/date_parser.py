from datetime import datetime, timezone
from dateparser import parse


class DateParser:

    @staticmethod
    def parse_date(value: str | None) -> datetime | None:
        if not value:
            return None

        dt = parse(
            value,
            settings={
                "RETURN_AS_TIMEZONE_AWARE": True,
                "TO_TIMEZONE": "UTC",
            },
        )

        if dt is None:
            return None

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)
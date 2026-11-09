from datetime import datetime, timedelta, timezone

MOSCOW = timezone(timedelta(hours=3), "Europe/Moscow")


def moscow_now() -> datetime:
    return datetime.now(MOSCOW)

import asyncio
from uuid import UUID, uuid4

from .models import Booking, EventType, IdempotencyResult

EVENT_TYPES: list[EventType] = [
    EventType(
        id=str(uuid4()),
        name="Знакомство",
        description=(
            "Короткий звонок, чтобы познакомиться, обсудить задачу "
            "и определить следующие шаги"
        ),
        duration_minutes=30,
    ),
    EventType(
        id=str(uuid4()),
        name="Консультация",
        description=(
            "Подробное обсуждение вашего вопроса, разбор возможных решений "
            "и следующих шагов"
        ),
        duration_minutes=60,
    ),
    EventType(
        id=str(uuid4()),
        name="Глубокий разбор",
        description=(
            "Детальный разбор сложной задачи и составление конкретного плана действий"
        ),
        duration_minutes=90,
    ),
]
BOOKINGS: list[Booking] = []
IDEMPOTENCY_RESULTS: dict[str, IdempotencyResult] = {}
BOOKING_LOCK = asyncio.Lock()


def find_event_type(value: object) -> EventType | None:
    if not isinstance(value, str):
        return None
    try:
        event_type_id = str(UUID(value))
    except ValueError:
        return None
    return next((item for item in EVENT_TYPES if item.id == event_type_id), None)

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

app = FastAPI(title="Call Calendar API", version="0.1.0")
MOSCOW_TIMEZONE = timezone(timedelta(hours=3))


def current_time() -> datetime:
    return datetime.now(MOSCOW_TIMEZONE)


class Health(BaseModel):
    status: str


class EventType(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    name: str
    description: str | None
    duration_minutes: int


class BookingBase(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: str
    starts_at: datetime
    ends_at: datetime


class LegacyBooking(BookingBase):
    id: str


class Booking(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    guest_name: str
    guest_email: str
    starts_at: datetime
    ends_at: datetime
    event_type: EventType


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
BOOKINGS: list[Booking | LegacyBooking] = []


@app.get("/api/health")
def health() -> Health:
    return Health(status="ok")


@app.get("/api/event-types")
def list_event_types() -> list[EventType]:
    return EVENT_TYPES


@app.get("/api/bookings", response_model=list[Booking])
def list_bookings(scope: str | None = None) -> list[Booking] | JSONResponse:
    if scope is None:
        code, message = "REQUIRED", "Укажите область списка"
    elif scope != "upcoming":
        code, message = "INVALID_SCOPE", "Допустимое значение scope: upcoming"
    else:
        now = current_time()
        upcoming = [
            booking
            for booking in BOOKINGS
            if isinstance(booking, Booking) and booking.ends_at > now
        ]
        return sorted(upcoming, key=lambda booking: booking.starts_at)
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "Проверьте введённые данные",
            "fieldErrors": [{"field": "scope", "code": code, "message": message}],
        },
    )


@app.post("/api/bookings", status_code=201)
def create_booking(booking: BookingBase) -> LegacyBooking:
    created = LegacyBooking(id=str(uuid4()), **booking.model_dump())
    BOOKINGS.append(created)
    return created

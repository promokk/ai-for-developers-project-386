import asyncio
import json
from contextlib import suppress
from dataclasses import dataclass
from datetime import date as calendar_date
from datetime import datetime, time, timedelta, timezone
from typing import Any, cast
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, field_serializer
from pydantic.alias_generators import to_camel

app = FastAPI(title="Call Calendar API", version="0.1.0")
MOSCOW = timezone(timedelta(hours=3), "Europe/Moscow")
FieldError = dict[str, str]
DURATION_MESSAGE = "Выберите длительность: 30, 60, 90 или 120 минут"
IDEMPOTENCY_REUSED_MESSAGE = (
    "Данные изменились после попытки отправки. Начните бронирование заново"
)


def current_time() -> datetime:
    return datetime.now(MOSCOW)


def moscow_now() -> datetime:
    return datetime.now(MOSCOW)


class Health(BaseModel):
    status: str


class EventType(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    name: str
    description: str | None
    duration_minutes: int


class Booking(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    guest_name: str
    guest_email: str
    starts_at: datetime
    ends_at: datetime
    event_type: EventType

    @field_serializer("starts_at", "ends_at")
    def serialize_time(self, value: datetime) -> str:
        return value.isoformat(timespec="minutes")


@dataclass
class IdempotencyResult:
    fingerprint: str
    status_code: int
    content: dict[str, Any]


class AvailabilityDay(BaseModel):
    date: str
    available_slots: int

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class AvailabilityInterval(BaseModel):
    starts_at: str
    ends_at: str
    available: bool

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Availability(BaseModel):
    date: str
    days: list[AvailabilityDay]
    intervals: list[AvailabilityInterval]

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


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


def api_error(
    status_code: int,
    code: str,
    message: str,
    field_errors: list[FieldError] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "message": message,
            "fieldErrors": field_errors or [],
        },
    )


def field_error(field: str, code: str, message: str) -> FieldError:
    return {"field": field, "code": code, "message": message}


def find_event_type(value: Any) -> EventType | None:
    if not isinstance(value, str):
        return None
    try:
        event_type_id = str(UUID(value))
    except ValueError:
        return None
    return next((item for item in EVENT_TYPES if item.id == event_type_id), None)


def validate_event_type_name(value: object) -> tuple[str, list[FieldError]]:
    if value is None:
        return "", [field_error("name", "REQUIRED", "Введите название")]
    if not isinstance(value, str):
        return "", [field_error("name", "INVALID_TYPE", "Название должно быть строкой")]
    name = value.strip()
    if not name:
        return name, [field_error("name", "REQUIRED", "Введите название")]
    if "\n" in name or "\r" in name:
        return name, [
            field_error("name", "NOT_SINGLE_LINE", "Название должно быть одной строкой")
        ]
    if len(name) > 100:
        return name, [
            field_error("name", "TOO_LONG", "Название не должно превышать 100 символов")
        ]
    return name, []


def validate_event_type_description(
    value: object,
) -> tuple[str | None, list[FieldError]]:
    if value is None:
        return None, []
    if not isinstance(value, str):
        return None, [
            field_error("description", "INVALID_TYPE", "Описание должно быть строкой")
        ]
    description = value.strip()
    if len(description) > 500:
        return description, [
            field_error(
                "description", "TOO_LONG", "Описание не должно превышать 500 символов"
            )
        ]
    return description or None, []


def validate_event_type_duration(value: object) -> tuple[int, list[FieldError]]:
    if value is None:
        return 0, [field_error("durationMinutes", "REQUIRED", DURATION_MESSAGE)]
    if type(value) is not int or value not in {30, 60, 90, 120}:
        return 0, [field_error("durationMinutes", "INVALID_DURATION", DURATION_MESSAGE)]
    return value, []


@app.get("/api/health")
def health() -> Health:
    return Health(status="ok")


@app.get("/api/event-types")
def list_event_types() -> list[EventType]:
    return EVENT_TYPES


@app.post("/api/event-types", status_code=201, response_model=EventType)
async def create_event_type(request: Request) -> EventType | JSONResponse:
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return api_error(400, "INVALID_JSON", "Некорректное тело запроса")
    if not isinstance(payload, dict):
        payload = {}

    name, name_errors = validate_event_type_name(payload.get("name"))
    description, description_errors = validate_event_type_description(
        payload.get("description")
    )
    duration, duration_errors = validate_event_type_duration(
        payload.get("durationMinutes")
    )
    unknown_errors = [
        field_error(field, "UNKNOWN_FIELD", "Неизвестное поле")
        for field in payload
        if field not in {"name", "description", "durationMinutes"}
    ]
    errors = [
        *name_errors,
        *description_errors,
        *duration_errors,
        *unknown_errors,
    ]
    if errors:
        return api_error(422, "VALIDATION_ERROR", "Проверьте введённые данные", errors)
    created = EventType(
        id=str(uuid4()),
        name=name,
        description=description,
        duration_minutes=duration,
    )
    EVENT_TYPES.append(created)
    return created


def request_fingerprint(payload: dict[str, Any]) -> str:
    normalized = dict(payload)
    for field in ("guestName", "guestEmail"):
        if isinstance(normalized.get(field), str):
            normalized[field] = normalized[field].strip()
    if isinstance(normalized.get("eventTypeId"), str):
        with suppress(ValueError):
            normalized["eventTypeId"] = str(UUID(normalized["eventTypeId"]))
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True)


def validate_guest_name(value: Any) -> FieldError | None:
    if value is None:
        return field_error("guestName", "REQUIRED", "Введите имя")
    if not isinstance(value, str):
        return field_error("guestName", "INVALID_TYPE", "Имя должно быть строкой")
    name = value.strip()
    if not name:
        return field_error("guestName", "REQUIRED", "Введите имя")
    if "\n" in name or "\r" in name:
        return field_error(
            "guestName", "NOT_SINGLE_LINE", "Имя должно быть одной строкой"
        )
    if len(name) > 100:
        return field_error(
            "guestName", "TOO_LONG", "Имя не должно превышать 100 символов"
        )
    return None


def validate_guest_email(value: Any) -> FieldError | None:
    if value is None:
        return field_error("guestEmail", "REQUIRED", "Введите email")
    if not isinstance(value, str):
        return field_error("guestEmail", "INVALID_TYPE", "Email должен быть строкой")
    email = value.strip()
    if not email:
        return field_error("guestEmail", "REQUIRED", "Введите email")
    if len(email) > 254:
        return field_error(
            "guestEmail", "TOO_LONG", "Email не должен превышать 254 символа"
        )
    parts = email.split("@")
    if (
        len(parts) != 2
        or not all(parts)
        or any(character.isspace() or ord(character) < 32 for character in email)
    ):
        return field_error("guestEmail", "INVALID_EMAIL", "Введите корректный email")
    return None


def parse_start(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M+03:00").replace(tzinfo=MOSCOW)
    except ValueError:
        return None
    return parsed if parsed.isoformat(timespec="minutes") == value else None


def validate_booking_time(
    starts_at: datetime, ends_at: datetime
) -> JSONResponse | None:
    first_day = moscow_now().date() + timedelta(days=1)
    code: str | None = None
    message = ""
    if not first_day <= starts_at.date() < first_day + timedelta(days=14):
        code = "START_OUTSIDE_BOOKING_WINDOW"
        message = "Дата должна входить в окно записи"
    elif starts_at.minute % 30:
        code = "START_NOT_ON_GRID"
        message = "Время должно следовать сетке 30 минут"
    elif starts_at.time() < time(9) or ends_at > datetime.combine(
        starts_at.date(), time(18), MOSCOW
    ):
        code = "OUTSIDE_BOOKING_HOURS"
        message = "Интервал должен целиком входить в часы записи 09:00-18:00"
    if code:
        return api_error(
            422,
            "VALIDATION_ERROR",
            "Проверьте введённые данные",
            [field_error("startsAt", code, message)],
        )
    return None


def validate_booking_payload(payload: dict[str, Any]) -> list[FieldError]:
    errors: list[FieldError] = []
    event_type_id = payload.get("eventTypeId")
    if event_type_id is None:
        errors.append(field_error("eventTypeId", "REQUIRED", "Выберите тип события"))
    elif not isinstance(event_type_id, str):
        errors.append(
            field_error(
                "eventTypeId",
                "INVALID_TYPE",
                "Идентификатор типа события должен быть строкой",
            )
        )
    starts_at = payload.get("startsAt")
    if starts_at is None:
        errors.append(field_error("startsAt", "REQUIRED", "Укажите время"))
    elif not isinstance(starts_at, str):
        errors.append(
            field_error("startsAt", "INVALID_TYPE", "Начало должно быть строкой")
        )
    elif parse_start(starts_at) is None:
        errors.append(
            field_error(
                "startsAt",
                "INVALID_DATETIME",
                "Укажите дату и время в формате "
                "ГГГГ-\u041c\u041c-ДДTЧЧ:\u041c\u041c+03:00",
            )
        )
    for validator, field in (
        (validate_guest_name, "guestName"),
        (validate_guest_email, "guestEmail"),
    ):
        error = validator(payload.get(field))
        if error:
            errors.append(error)
    allowed_fields = {"eventTypeId", "startsAt", "guestName", "guestEmail"}
    errors.extend(
        field_error(field, "UNKNOWN_FIELD", "Неизвестное поле")
        for field in payload
        if field not in allowed_fields
    )
    return errors


def intervals_for(
    event_type: EventType, day: calendar_date
) -> list[AvailabilityInterval]:
    intervals: list[AvailabilityInterval] = []
    start = datetime.combine(day, time(9), MOSCOW)
    close = datetime.combine(day, time(18), MOSCOW)
    while start + timedelta(minutes=event_type.duration_minutes) <= close:
        end = start + timedelta(minutes=event_type.duration_minutes)
        intervals.append(
            AvailabilityInterval(
                starts_at=start.isoformat(timespec="minutes"),
                ends_at=end.isoformat(timespec="minutes"),
                available=not any(
                    booking.starts_at < end and start < booking.ends_at
                    for booking in BOOKINGS
                ),
            )
        )
        start += timedelta(minutes=30)
    return intervals


@app.get("/api/event-types/{eventTypeId}/availability", response_model=Availability)
def get_availability(
    eventTypeId: str, date: str | None = None
) -> Availability | JSONResponse:
    event_type = find_event_type(eventTypeId)
    if event_type is None:
        return api_error(404, "EVENT_TYPE_NOT_FOUND", "Тип события не найден")
    if date is None:
        return api_error(
            422,
            "VALIDATION_ERROR",
            "Проверьте введённые данные",
            [field_error("date", "REQUIRED", "Укажите дату")],
        )
    try:
        requested_date = calendar_date.fromisoformat(date)
        if requested_date.isoformat() != date:
            raise ValueError
    except ValueError:
        return api_error(
            422,
            "VALIDATION_ERROR",
            "Проверьте введённые данные",
            [
                field_error(
                    "date",
                    "INVALID_DATE",
                    "Укажите существующую дату в формате ГГГГ-\u041c\u041c-ДД",
                )
            ],
        )
    first_day = moscow_now().date() + timedelta(days=1)
    if not first_day <= requested_date < first_day + timedelta(days=14):
        return api_error(
            422,
            "VALIDATION_ERROR",
            "Проверьте введённые данные",
            [
                field_error(
                    "date",
                    "DATE_OUTSIDE_BOOKING_WINDOW",
                    "Дата должна входить в окно записи",
                )
            ],
        )
    days = []
    for offset in range(14):
        day = first_day + timedelta(days=offset)
        intervals = intervals_for(event_type, day)
        days.append(
            AvailabilityDay(
                date=day.isoformat(),
                available_slots=sum(interval.available for interval in intervals),
            )
        )
    return Availability(
        date=date,
        days=days,
        intervals=intervals_for(event_type, requested_date),
    )


@app.get("/api/bookings", response_model=list[Booking])
def list_bookings(scope: str | None = None) -> list[Booking] | JSONResponse:
    if scope is None:
        code, message = "REQUIRED", "Укажите область списка"
    elif scope != "upcoming":
        code, message = "INVALID_SCOPE", "Допустимое значение scope: upcoming"
    else:
        upcoming = [booking for booking in BOOKINGS if booking.ends_at > current_time()]
        return sorted(upcoming, key=lambda booking: booking.starts_at)
    return api_error(
        422,
        "VALIDATION_ERROR",
        "Проверьте введённые данные",
        [field_error("scope", code, message)],
    )


async def commit_booking(
    key: str,
    fingerprint: str,
    payload: dict[str, Any],
    event_type: EventType,
    starts_at: datetime,
) -> Booking | JSONResponse:
    async with BOOKING_LOCK:
        saved = IDEMPOTENCY_RESULTS.get(key)
        if saved:
            if saved.fingerprint != fingerprint:
                return api_error(
                    409,
                    "IDEMPOTENCY_KEY_REUSED",
                    IDEMPOTENCY_REUSED_MESSAGE,
                )
            return JSONResponse(status_code=saved.status_code, content=saved.content)
        ends_at = starts_at + timedelta(minutes=event_type.duration_minutes)
        if any(
            booking.starts_at < ends_at and starts_at < booking.ends_at
            for booking in BOOKINGS
        ):
            content = {
                "code": "SLOT_CONFLICT",
                "message": "Это время уже занято",
                "fieldErrors": [],
            }
            IDEMPOTENCY_RESULTS[key] = IdempotencyResult(fingerprint, 409, content)
            return JSONResponse(status_code=409, content=content)
        created = Booking(
            id=str(uuid4()),
            guest_name=payload["guestName"].strip(),
            guest_email=payload["guestEmail"].strip(),
            starts_at=starts_at,
            ends_at=ends_at,
            event_type=event_type,
        )
        BOOKINGS.append(created)
        IDEMPOTENCY_RESULTS[key] = IdempotencyResult(
            fingerprint=fingerprint,
            status_code=201,
            content=created.model_dump(mode="json", by_alias=True),
        )
        return created


@app.post("/api/bookings", status_code=201, response_model=Booking)
async def create_booking(request: Request) -> Booking | JSONResponse:
    raw_key = request.headers.get("Idempotency-Key")
    if raw_key is None:
        return api_error(
            422,
            "VALIDATION_ERROR",
            "Проверьте введённые данные",
            [
                field_error(
                    "Idempotency-Key", "REQUIRED", "Укажите ключ идемпотентности"
                )
            ],
        )
    try:
        key = str(UUID(raw_key))
    except ValueError:
        return api_error(
            422,
            "VALIDATION_ERROR",
            "Проверьте введённые данные",
            [
                field_error(
                    "Idempotency-Key",
                    "INVALID_IDEMPOTENCY_KEY",
                    "Ключ идемпотентности должен быть UUID",
                )
            ],
        )
    try:
        payload = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return api_error(400, "INVALID_JSON", "Некорректное тело запроса")
    if not isinstance(payload, dict):
        return api_error(400, "INVALID_JSON", "Некорректное тело запроса")
    fingerprint = request_fingerprint(payload)
    saved = IDEMPOTENCY_RESULTS.get(key)
    if saved:
        if saved.fingerprint != fingerprint:
            return api_error(
                409,
                "IDEMPOTENCY_KEY_REUSED",
                IDEMPOTENCY_REUSED_MESSAGE,
            )
        return JSONResponse(status_code=saved.status_code, content=saved.content)
    errors = validate_booking_payload(payload)
    if errors:
        return api_error(422, "VALIDATION_ERROR", "Проверьте введённые данные", errors)
    event_type = find_event_type(payload["eventTypeId"])
    if event_type is None:
        return api_error(404, "EVENT_TYPE_NOT_FOUND", "Тип события не найден")
    starts_at = cast(datetime, parse_start(payload["startsAt"]))
    ends_at = starts_at + timedelta(minutes=event_type.duration_minutes)
    time_error = validate_booking_time(starts_at, ends_at)
    if time_error:
        return time_error
    return await commit_booking(key, fingerprint, payload, event_type, starts_at)

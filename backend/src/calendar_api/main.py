import json
from datetime import datetime
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

app = FastAPI(title="Call Calendar API", version="0.1.0")


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


class Booking(BookingBase):
    id: str


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


@app.get("/api/health")
def health() -> Health:
    return Health(status="ok")


@app.get("/api/event-types")
def list_event_types() -> list[EventType]:
    return EVENT_TYPES


FieldError = dict[str, str]
DURATION_MESSAGE = "Выберите длительность: 30, 60, 90 или 120 минут"


def field_error(field: str, code: str, message: str) -> FieldError:
    return {"field": field, "code": code, "message": message}


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


def event_type_validation_response(field_errors: list[FieldError]) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "Проверьте введённые данные",
            "fieldErrors": field_errors,
        },
    )


@app.post("/api/event-types", status_code=201, response_model=EventType)
async def create_event_type(request: Request) -> EventType | JSONResponse:
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={
                "code": "INVALID_JSON",
                "message": "Некорректное тело запроса",
                "fieldErrors": [],
            },
        )
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
        return event_type_validation_response(errors)
    created = EventType(
        id=str(uuid4()),
        name=name,
        description=description,
        duration_minutes=duration,
    )
    EVENT_TYPES.append(created)
    return created


@app.get("/api/bookings")
def list_bookings() -> list[Booking]:
    return BOOKINGS


@app.post("/api/bookings", status_code=201)
def create_booking(booking: BookingBase) -> Booking:
    created = Booking(id=str(uuid4()), **booking.model_dump())
    BOOKINGS.append(created)
    return created

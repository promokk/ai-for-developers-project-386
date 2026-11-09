from typing import Any
from uuid import uuid4

from fastapi.responses import JSONResponse

from .errors import api_error, field_error
from .models import EventType
from .store import EVENT_TYPES
from .validation import (
    validate_event_type_description,
    validate_event_type_duration,
    validate_event_type_name,
)


def list_event_types() -> list[EventType]:
    return EVENT_TYPES


def create_event_type(payload: dict[str, Any]) -> EventType | JSONResponse:
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

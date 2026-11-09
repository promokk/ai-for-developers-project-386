import unicodedata
from datetime import datetime, time, timedelta
from typing import Any

from fastapi.responses import JSONResponse

from . import clock
from .clock import MOSCOW
from .errors import FieldError, api_error, field_error

DURATION_MESSAGE = "Выберите длительность: 30, 60, 90 или 120 минут"


def validate_single_line_name(
    value: object, field: str, label: str
) -> tuple[str, list[FieldError]]:
    if value is None:
        return "", [field_error(field, "REQUIRED", f"Введите {label}")]
    if not isinstance(value, str):
        return "", [
            field_error(
                field, "INVALID_TYPE", f"{label.capitalize()} должно быть строкой"
            )
        ]
    name = value.strip()
    if not name:
        return name, [field_error(field, "REQUIRED", f"Введите {label}")]
    if "\n" in name or "\r" in name:
        return name, [
            field_error(
                field,
                "NOT_SINGLE_LINE",
                f"{label.capitalize()} должно быть одной строкой",
            )
        ]
    if len(name) > 100:
        return name, [
            field_error(
                field,
                "TOO_LONG",
                f"{label.capitalize()} не должно превышать 100 символов",
            )
        ]
    return name, []


def validate_event_type_name(value: object) -> tuple[str, list[FieldError]]:
    return validate_single_line_name(value, "name", "название")


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


def validate_guest_name(value: Any) -> FieldError | None:
    _, errors = validate_single_line_name(value, "guestName", "имя")
    return errors[0] if errors else None


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
        or any(
            character.isspace() or unicodedata.category(character) == "Cc"
            for character in email
        )
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
    first_day = clock.moscow_now().date() + timedelta(days=1)
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

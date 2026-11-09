import json
from contextlib import suppress
from datetime import datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

from fastapi.responses import JSONResponse

from . import clock
from .errors import api_error, field_error
from .models import Booking, EventType, IdempotencyResult
from .store import BOOKING_LOCK, BOOKINGS, IDEMPOTENCY_RESULTS, find_event_type
from .validation import parse_start, validate_booking_payload, validate_booking_time

IDEMPOTENCY_REUSED_MESSAGE = (
    "Данные изменились после попытки отправки. Начните бронирование заново"
)


def request_fingerprint(payload: dict[str, Any]) -> str:
    normalized = dict(payload)
    for field in ("guestName", "guestEmail"):
        if isinstance(normalized.get(field), str):
            normalized[field] = normalized[field].strip()
    if isinstance(normalized.get("eventTypeId"), str):
        with suppress(ValueError):
            normalized["eventTypeId"] = str(UUID(normalized["eventTypeId"]))
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True)


def list_bookings(scope: str | None) -> list[Booking] | JSONResponse:
    if scope is None:
        code, message = "REQUIRED", "Укажите область списка"
    elif scope != "upcoming":
        code, message = "INVALID_SCOPE", "Допустимое значение scope: upcoming"
    else:
        upcoming = [
            booking for booking in BOOKINGS if booking.ends_at > clock.moscow_now()
        ]
        return sorted(upcoming, key=lambda booking: booking.starts_at)
    return api_error(
        422,
        "VALIDATION_ERROR",
        "Проверьте введённые данные",
        [field_error("scope", code, message)],
    )


def replay_idempotency_result(key: str, fingerprint: str) -> JSONResponse | None:
    saved = IDEMPOTENCY_RESULTS.get(key)
    if saved is None:
        return None
    if saved.fingerprint != fingerprint:
        return api_error(
            409,
            "IDEMPOTENCY_KEY_REUSED",
            IDEMPOTENCY_REUSED_MESSAGE,
        )
    return JSONResponse(status_code=saved.status_code, content=saved.content)


async def commit_booking(
    key: str,
    fingerprint: str,
    payload: dict[str, Any],
    event_type: EventType,
    starts_at: datetime,
) -> Booking | JSONResponse:
    async with BOOKING_LOCK:
        replay = replay_idempotency_result(key, fingerprint)
        if replay is not None:
            return replay
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


def normalize_idempotency_key(raw_key: str | None) -> str | JSONResponse:
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
        return str(UUID(raw_key))
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


async def create_booking(key: str, payload: dict[str, Any]) -> Booking | JSONResponse:
    fingerprint = request_fingerprint(payload)
    replay = replay_idempotency_result(key, fingerprint)
    if replay is not None:
        return replay
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

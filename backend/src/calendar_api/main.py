import json
from typing import Annotated, Any

from fastapi import FastAPI, Path, Request
from fastapi.responses import JSONResponse

from .availability import availability_for
from .bookings import create_booking as create_booking_record
from .bookings import list_bookings as list_booking_records
from .bookings import normalize_idempotency_key
from .errors import api_error
from .event_types import create_event_type as create_event_type_record
from .event_types import list_event_types as list_event_type_records
from .models import Availability, Booking, EventType, Health
from .store import BOOKINGS as BOOKINGS
from .store import EVENT_TYPES as EVENT_TYPES
from .store import IDEMPOTENCY_RESULTS as IDEMPOTENCY_RESULTS

app = FastAPI(title="Call Calendar API", version="0.1.0")


@app.get("/api/health")
def health() -> Health:
    return Health(status="ok")


@app.get("/api/event-types")
def list_event_types() -> list[EventType]:
    return list_event_type_records()


@app.post("/api/event-types", status_code=201, response_model=EventType)
async def create_event_type(request: Request) -> EventType | JSONResponse:
    try:
        payload = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return api_error(400, "INVALID_JSON", "Некорректное тело запроса")
    if not isinstance(payload, dict):
        payload = {}
    return create_event_type_record(payload)


@app.get("/api/event-types/{eventTypeId}/availability", response_model=Availability)
async def get_availability(
    event_type_id: Annotated[str, Path(alias="eventTypeId")],
    date: str | None = None,
) -> Availability | JSONResponse:
    return await availability_for(event_type_id, date)


@app.get("/api/bookings", response_model=list[Booking])
def list_bookings(scope: str | None = None) -> list[Booking] | JSONResponse:
    return list_booking_records(scope)


@app.post("/api/bookings", status_code=201, response_model=Booking)
async def create_booking(request: Request) -> Booking | JSONResponse:
    key = normalize_idempotency_key(request.headers.get("Idempotency-Key"))
    if isinstance(key, JSONResponse):
        return key
    try:
        payload: Any = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return api_error(400, "INVALID_JSON", "Некорректное тело запроса")
    if not isinstance(payload, dict):
        return api_error(400, "INVALID_JSON", "Некорректное тело запроса")
    return await create_booking_record(key, payload)

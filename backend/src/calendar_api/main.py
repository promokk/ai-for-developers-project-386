import json
import os
from pathlib import Path as FilePath
from typing import Annotated, Any

from fastapi import APIRouter, FastAPI, HTTPException, Path, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

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

router = APIRouter()


@router.get("/api/health")
def health() -> Health:
    return Health(status="ok")


@router.get("/api/event-types")
def list_event_types() -> list[EventType]:
    return list_event_type_records()


@router.post("/api/event-types", status_code=201, response_model=EventType)
async def create_event_type(request: Request) -> EventType | JSONResponse:
    try:
        payload = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return api_error(400, "INVALID_JSON", "Некорректное тело запроса")
    if not isinstance(payload, dict):
        payload = {}
    return create_event_type_record(payload)


@router.get("/api/event-types/{eventTypeId}/availability", response_model=Availability)
async def get_availability(
    event_type_id: Annotated[str, Path(alias="eventTypeId")],
    date: str | None = None,
) -> Availability | JSONResponse:
    return await availability_for(event_type_id, date)


@router.get("/api/bookings", response_model=list[Booking])
def list_bookings(scope: str | None = None) -> list[Booking] | JSONResponse:
    return list_booking_records(scope)


@router.post("/api/bookings", status_code=201, response_model=Booking)
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


def create_app(static_dir: FilePath | None = None) -> FastAPI:
    app = FastAPI(title="Call Calendar API", version="0.1.0")
    app.include_router(router)

    if static_dir is not None and static_dir.is_dir():
        assets_dir = static_dir / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str) -> FileResponse:
            if path == "api" or path.startswith("api/"):
                raise HTTPException(status_code=404)
            return FileResponse(static_dir / "index.html")

    return app


app = create_app(
    FilePath(
        os.environ.get("CALENDAR_STATIC_DIR", str(FilePath(__file__).parent / "static"))
    )
)

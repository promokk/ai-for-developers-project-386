import argparse
import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime

import uvicorn
from calendar_api import clock
from calendar_api.main import BOOKINGS, EVENT_TYPES, Booking, app
from fastapi import Request, Response
from fastapi.responses import JSONResponse

parser = argparse.ArgumentParser()
parser.add_argument("--delay", type=float, default=0)
parser.add_argument("--empty", action="store_true")
parser.add_argument("--failures", type=int, default=0)
parser.add_argument("--booking-failures", type=int, default=0)
parser.add_argument("--booking-delay", type=float, default=0)
parser.add_argument("--drop-booking-response", type=int, default=0)
parser.add_argument("--agenda", action="store_true")
parser.add_argument("--now")
args = parser.parse_args()
remaining_failures = args.failures
remaining_booking_failures = args.booking_failures
remaining_booking_delays = 1 if args.booking_delay else 0
remaining_dropped_responses = args.drop_booking_response
if args.empty:
    EVENT_TYPES.clear()
if args.now:
    fixed_now = datetime.fromisoformat(args.now)

    def fixed_time() -> datetime:
        return fixed_now

    clock.moscow_now = fixed_time
if args.agenda:
    BOOKINGS.extend(
        [
            Booking(
                id="tomorrow-booking-id",
                guest_name="Мария Волкова",
                guest_email="maria@example.com",
                starts_at=datetime.fromisoformat("2026-03-28T09:00:00+03:00"),
                ends_at=datetime.fromisoformat("2026-03-28T10:00:00+03:00"),
                event_type=EVENT_TYPES[1],
            ),
            Booking(
                id="current-booking-id",
                guest_name="Анна Смирнова",
                guest_email="anna@example.com",
                starts_at=datetime.fromisoformat("2026-03-27T11:30:00+03:00"),
                ends_at=datetime.fromisoformat("2026-03-27T12:30:00+03:00"),
                event_type=EVENT_TYPES[0],
            ),
            Booking(
                id="later-booking-id",
                guest_name="Игорь Петров",
                guest_email="igor@example.com",
                starts_at=datetime.fromisoformat("2026-03-27T14:00:00+03:00"),
                ends_at=datetime.fromisoformat("2026-03-27T15:30:00+03:00"),
                event_type=EVENT_TYPES[2],
            ),
            Booking(
                id="past-booking-id",
                guest_name="Прошедший звонок",
                guest_email="past@example.com",
                starts_at=datetime.fromisoformat("2026-03-27T09:00:00+03:00"),
                ends_at=datetime.fromisoformat("2026-03-27T10:00:00+03:00"),
                event_type=EVENT_TYPES[1],
            ),
        ]
    )


@app.middleware("http")
async def control_event_types(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    global remaining_failures
    global remaining_booking_failures
    global remaining_booking_delays
    global remaining_dropped_responses
    if request.url.path == "/api/event-types":
        if remaining_failures:
            remaining_failures -= 1
            return JSONResponse(status_code=503, content={})
        if args.delay:
            await asyncio.sleep(args.delay)
    if request.url.path == "/api/bookings" and request.method == "POST":
        if remaining_booking_failures:
            remaining_booking_failures -= 1
            return JSONResponse(status_code=503, content={})
        if remaining_booking_delays:
            remaining_booking_delays -= 1
            await asyncio.sleep(args.booking_delay)
        response = await call_next(request)
        if remaining_dropped_responses:
            remaining_dropped_responses -= 1
            return JSONResponse(status_code=503, content={})
        return response
    return await call_next(request)


uvicorn.run(app, host="127.0.0.1", port=8001)

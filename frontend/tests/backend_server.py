import argparse
import asyncio

import uvicorn
from calendar_api.main import EVENT_TYPES, app
from fastapi.responses import JSONResponse

parser = argparse.ArgumentParser()
parser.add_argument("--delay", type=float, default=0)
parser.add_argument("--empty", action="store_true")
parser.add_argument("--failures", type=int, default=0)
parser.add_argument("--booking-failures", type=int, default=0)
parser.add_argument("--booking-delay", type=float, default=0)
parser.add_argument("--drop-booking-response", type=int, default=0)
args = parser.parse_args()
remaining_failures = args.failures
remaining_booking_failures = args.booking_failures
remaining_booking_delays = 1 if args.booking_delay else 0
remaining_dropped_responses = args.drop_booking_response
if args.empty:
    EVENT_TYPES.clear()


@app.middleware("http")
async def control_event_types(request, call_next):
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

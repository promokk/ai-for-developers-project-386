import argparse
import asyncio

import uvicorn
from calendar_api.main import EVENT_TYPES, app
from fastapi.responses import JSONResponse

parser = argparse.ArgumentParser()
parser.add_argument("--delay", type=float, default=0)
parser.add_argument("--empty", action="store_true")
parser.add_argument("--failures", type=int, default=0)
args = parser.parse_args()
remaining_failures = args.failures
if args.empty:
    EVENT_TYPES.clear()


@app.middleware("http")
async def control_event_types(request, call_next):
    global remaining_failures
    if request.url.path == "/api/event-types":
        if remaining_failures:
            remaining_failures -= 1
            return JSONResponse(status_code=503, content={})
        if args.delay:
            await asyncio.sleep(args.delay)
    return await call_next(request)


uvicorn.run(app, host="127.0.0.1", port=8000)

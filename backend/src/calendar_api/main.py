from datetime import datetime
from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

app = FastAPI(title="Call Calendar API", version="0.1.0")


class Health(BaseModel):
    status: str


class BookingBase(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: str
    starts_at: datetime
    ends_at: datetime


class Booking(BookingBase):
    id: str


BOOKINGS: list[Booking] = []


@app.get("/api/health")
def health() -> Health:
    return Health(status="ok")


@app.get("/api/bookings")
def list_bookings() -> list[Booking]:
    return BOOKINGS


@app.post("/api/bookings", status_code=201)
def create_booking(booking: BookingBase) -> Booking:
    created = Booking(id=str(uuid4()), **booking.model_dump())
    BOOKINGS.append(created)
    return created

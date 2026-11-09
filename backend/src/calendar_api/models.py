from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_serializer
from pydantic.alias_generators import to_camel


class Health(BaseModel):
    status: str


class EventType(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    name: str
    description: str | None
    duration_minutes: int


class Booking(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    guest_name: str
    guest_email: str
    starts_at: datetime
    ends_at: datetime
    event_type: EventType

    @field_serializer("starts_at", "ends_at")
    def serialize_time(self, value: datetime) -> str:
        return value.isoformat(timespec="minutes")


@dataclass
class IdempotencyResult:
    fingerprint: str
    status_code: int
    content: dict[str, Any]


class AvailabilityDay(BaseModel):
    date: str
    available_slots: int

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class AvailabilityInterval(BaseModel):
    starts_at: str
    ends_at: str
    available: bool

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Availability(BaseModel):
    date: str
    days: list[AvailabilityDay]
    intervals: list[AvailabilityInterval]

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

import asyncio
from datetime import date as calendar_date
from datetime import datetime, time, timedelta

from fastapi.responses import JSONResponse

from . import clock
from .clock import MOSCOW
from .errors import api_error, field_error
from .models import (
    Availability,
    AvailabilityDay,
    AvailabilityInterval,
    Booking,
    EventType,
)
from .store import BOOKING_LOCK, BOOKINGS, find_event_type


def intervals_for(
    event_type: EventType, day: calendar_date, bookings: list[Booking]
) -> list[AvailabilityInterval]:
    intervals: list[AvailabilityInterval] = []
    start = datetime.combine(day, time(9), MOSCOW)
    close = datetime.combine(day, time(18), MOSCOW)
    while start + timedelta(minutes=event_type.duration_minutes) <= close:
        end = start + timedelta(minutes=event_type.duration_minutes)
        intervals.append(
            AvailabilityInterval(
                starts_at=start.isoformat(timespec="minutes"),
                ends_at=end.isoformat(timespec="minutes"),
                available=not any(
                    booking.starts_at < end and start < booking.ends_at
                    for booking in bookings
                ),
            )
        )
        start += timedelta(minutes=30)
    return intervals


def build_availability(
    event_type: EventType,
    requested_date: calendar_date,
    first_day: calendar_date,
    bookings: list[Booking],
) -> Availability:
    days = []
    for offset in range(14):
        day = first_day + timedelta(days=offset)
        intervals = intervals_for(event_type, day, bookings)
        days.append(
            AvailabilityDay(
                date=day.isoformat(),
                available_slots=sum(interval.available for interval in intervals),
            )
        )
    return Availability(
        date=requested_date.isoformat(),
        days=days,
        intervals=intervals_for(event_type, requested_date, bookings),
    )


async def availability_for(
    event_type_id: str, date: str | None
) -> Availability | JSONResponse:
    event_type = find_event_type(event_type_id)
    if event_type is None:
        return api_error(404, "EVENT_TYPE_NOT_FOUND", "Тип события не найден")
    if date is None:
        return api_error(
            422,
            "VALIDATION_ERROR",
            "Проверьте введённые данные",
            [field_error("date", "REQUIRED", "Укажите дату")],
        )
    try:
        requested_date = calendar_date.fromisoformat(date)
        if requested_date.isoformat() != date:
            raise ValueError
    except ValueError:
        return api_error(
            422,
            "VALIDATION_ERROR",
            "Проверьте введённые данные",
            [
                field_error(
                    "date",
                    "INVALID_DATE",
                    "Укажите существующую дату в формате ГГГГ-\u041c\u041c-ДД",
                )
            ],
        )
    first_day = clock.moscow_now().date() + timedelta(days=1)
    if not first_day <= requested_date < first_day + timedelta(days=14):
        return api_error(
            422,
            "VALIDATION_ERROR",
            "Проверьте введённые данные",
            [
                field_error(
                    "date",
                    "DATE_OUTSIDE_BOOKING_WINDOW",
                    "Дата должна входить в окно записи",
                )
            ],
        )
    async with BOOKING_LOCK:
        bookings = BOOKINGS.copy()
    return await asyncio.to_thread(
        build_availability, event_type, requested_date, first_day, bookings
    )

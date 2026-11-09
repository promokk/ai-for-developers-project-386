from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Event
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import calendar_api.availability as availability
from calendar_api.main import app

client = TestClient(app)
MOSCOW = timezone(timedelta(hours=3), "Europe/Moscow")


def test_availability_returns_fourteen_days_and_all_intervals() -> None:
    event_type = client.get("/api/event-types").json()[0]
    tomorrow = datetime.now(MOSCOW).date() + timedelta(days=1)

    response = client.get(
        f"/api/event-types/{event_type['id']}/availability",
        params={"date": tomorrow.isoformat()},
    )

    assert response.status_code == 200
    availability = response.json()
    assert availability["date"] == tomorrow.isoformat()
    assert [day["date"] for day in availability["days"]] == [
        (tomorrow + timedelta(days=offset)).isoformat() for offset in range(14)
    ]
    assert all(day["availableSlots"] == 18 for day in availability["days"])
    assert len(availability["intervals"]) == 18
    assert availability["intervals"][0] == {
        "startsAt": f"{tomorrow.isoformat()}T09:00+03:00",
        "endsAt": f"{tomorrow.isoformat()}T09:30+03:00",
        "available": True,
    }
    assert availability["intervals"][-1] == {
        "startsAt": f"{tomorrow.isoformat()}T17:30+03:00",
        "endsAt": f"{tomorrow.isoformat()}T18:00+03:00",
        "available": True,
    }


def test_availability_marks_booked_interval_and_updates_only_its_day() -> None:
    event_type = client.get("/api/event-types").json()[0]
    tomorrow = datetime.now(MOSCOW).date() + timedelta(days=1)
    starts_at = f"{tomorrow.isoformat()}T09:00+03:00"
    created = client.post(
        "/api/bookings",
        json={
            "eventTypeId": event_type["id"],
            "startsAt": starts_at,
            "guestName": "Иван",
            "guestEmail": "ivan@example.com",
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert created.status_code == 201

    response = client.get(
        f"/api/event-types/{event_type['id']}/availability",
        params={"date": tomorrow.isoformat()},
    )

    availability = response.json()
    assert availability["days"][0]["availableSlots"] == 17
    assert availability["days"][1]["availableSlots"] == 18
    assert availability["intervals"][0] == {
        "startsAt": starts_at,
        "endsAt": f"{tomorrow.isoformat()}T09:30+03:00",
        "available": False,
    }
    assert availability["intervals"][1]["available"] is True


def test_availability_stays_consistent_during_concurrent_booking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event_type = client.get("/api/event-types").json()[0]
    tomorrow = datetime.now(MOSCOW).date() + timedelta(days=1)
    days_computed = Event()
    finish_availability = Event()
    original_intervals_for = availability.intervals_for
    calls = 0

    def pause_before_requested_date(event_type, day, *args):
        nonlocal calls
        intervals = original_intervals_for(event_type, day, *args)
        calls += 1
        if calls == 14:
            days_computed.set()
            assert finish_availability.wait(timeout=5)
        return intervals

    monkeypatch.setattr(availability, "intervals_for", pause_before_requested_date)
    url = f"/api/event-types/{event_type['id']}/availability"
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending_availability = pool.submit(
            client.get, url, params={"date": tomorrow.isoformat()}
        )
        try:
            assert days_computed.wait(timeout=5)
            created = client.post(
                "/api/bookings",
                json={
                    "eventTypeId": event_type["id"],
                    "startsAt": f"{tomorrow.isoformat()}T09:00+03:00",
                    "guestName": "Иван",
                    "guestEmail": "ivan@example.com",
                },
                headers={"Idempotency-Key": str(uuid4())},
            )
            assert created.status_code == 201
        finally:
            finish_availability.set()
        response = pending_availability.result(timeout=5)

    assert response.status_code == 200
    result = response.json()
    assert result["days"][0]["availableSlots"] == sum(
        interval["available"] for interval in result["intervals"]
    )


def test_availability_rejects_unknown_or_malformed_event_type() -> None:
    for event_type_id in (str(uuid4()), "not-a-uuid"):
        response = client.get(
            f"/api/event-types/{event_type_id}/availability",
            params={
                "date": (datetime.now(MOSCOW).date() + timedelta(days=1)).isoformat()
            },
        )

        assert response.status_code == 404
        assert response.json() == {
            "code": "EVENT_TYPE_NOT_FOUND",
            "message": "Тип события не найден",
            "fieldErrors": [],
        }


@pytest.mark.parametrize(
    ("date", "code", "message"),
    [
        (None, "REQUIRED", "Укажите дату"),
        (
            "2026-02-30",
            "INVALID_DATE",
            "Укажите существующую дату в формате ГГГГ-\u041c\u041c-\u0414\u0414",
        ),
        (
            "30.01.2026",
            "INVALID_DATE",
            "Укажите существующую дату в формате ГГГГ-\u041c\u041c-\u0414\u0414",
        ),
    ],
)
def test_availability_validates_date_format(
    date: str | None, code: str, message: str
) -> None:
    event_type = client.get("/api/event-types").json()[0]
    params = {} if date is None else {"date": date}

    response = client.get(
        f"/api/event-types/{event_type['id']}/availability", params=params
    )

    assert response.status_code == 422
    assert response.json() == {
        "code": "VALIDATION_ERROR",
        "message": "Проверьте введённые данные",
        "fieldErrors": [{"field": "date", "code": code, "message": message}],
    }


@pytest.mark.parametrize("offset", [0, 15])
def test_availability_rejects_dates_outside_booking_window(offset: int) -> None:
    event_type = client.get("/api/event-types").json()[0]
    date = datetime.now(MOSCOW).date() + timedelta(days=offset)

    response = client.get(
        f"/api/event-types/{event_type['id']}/availability",
        params={"date": date.isoformat()},
    )

    assert response.status_code == 422
    assert response.json()["fieldErrors"] == [
        {
            "field": "date",
            "code": "DATE_OUTSIDE_BOOKING_WINDOW",
            "message": "Дата должна входить в окно записи",
        }
    ]


@pytest.mark.parametrize(
    ("duration", "count", "last_start", "last_end"),
    [
        (30, 18, "17:30", "18:00"),
        (60, 17, "17:00", "18:00"),
        (90, 16, "16:30", "18:00"),
        (120, 15, "16:00", "18:00"),
    ],
)
def test_availability_respects_duration_on_thirty_minute_grid(
    duration: int, count: int, last_start: str, last_end: str
) -> None:
    event_types = client.get("/api/event-types").json()
    event_type = next(
        (item for item in event_types if item["durationMinutes"] == duration),
        None,
    )
    if event_type is None:
        created = client.post(
            "/api/event-types",
            json={"name": "Длинная сессия", "durationMinutes": duration},
        )
        assert created.status_code == 201
        event_type = created.json()
    tomorrow = datetime.now(MOSCOW).date() + timedelta(days=1)

    response = client.get(
        f"/api/event-types/{event_type['id']}/availability",
        params={"date": tomorrow.isoformat()},
    )

    intervals = response.json()["intervals"]
    assert len(intervals) == count
    assert response.json()["days"][0]["availableSlots"] == count
    assert intervals[0]["startsAt"] == f"{tomorrow.isoformat()}T09:00+03:00"
    assert intervals[-1]["startsAt"] == f"{tomorrow.isoformat()}T{last_start}+03:00"
    assert intervals[-1]["endsAt"] == f"{tomorrow.isoformat()}T{last_end}+03:00"


def test_availability_keeps_structure_when_entire_window_is_booked() -> None:
    event_type = client.get("/api/event-types").json()[0]
    tomorrow = datetime.now(MOSCOW).date() + timedelta(days=1)
    for day_offset in range(14):
        day = tomorrow + timedelta(days=day_offset)
        for slot in range(18):
            hour = 9 + slot // 2
            minute = "30" if slot % 2 else "00"
            response = client.post(
                "/api/bookings",
                json={
                    "eventTypeId": event_type["id"],
                    "startsAt": f"{day.isoformat()}T{hour:02}:{minute}+03:00",
                    "guestName": "Гость",
                    "guestEmail": "guest@example.com",
                },
                headers={"Idempotency-Key": str(uuid4())},
            )
            assert response.status_code == 201

    response = client.get(
        f"/api/event-types/{event_type['id']}/availability",
        params={"date": tomorrow.isoformat()},
    )

    assert response.status_code == 200
    availability = response.json()
    assert len(availability["days"]) == 14
    assert all(day["availableSlots"] == 0 for day in availability["days"])
    assert len(availability["intervals"]) == 18
    assert all(not interval["available"] for interval in availability["intervals"])

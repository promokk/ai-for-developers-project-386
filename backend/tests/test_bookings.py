from collections.abc import Iterator
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from calendar_api.main import BOOKINGS, EVENT_TYPES, Booking, app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_bookings() -> Iterator[None]:
    BOOKINGS.clear()
    yield
    BOOKINGS.clear()


def add_booking(
    booking_id: str,
    event_type_index: int,
    guest_name: str,
    guest_email: str,
    starts_at: str,
    ends_at: str,
) -> None:
    BOOKINGS.append(
        Booking(
            id=booking_id,
            guest_name=guest_name,
            guest_email=guest_email,
            starts_at=datetime.fromisoformat(starts_at),
            ends_at=datetime.fromisoformat(ends_at),
            event_type=EVENT_TYPES[event_type_index],
        )
    )


@pytest.mark.parametrize(
    ("query", "code", "message"),
    [
        ("", "REQUIRED", "Укажите область списка"),
        ("?scope=all", "INVALID_SCOPE", "Допустимое значение scope: upcoming"),
    ],
)
def test_list_bookings_requires_upcoming_scope(
    query: str, code: str, message: str
) -> None:
    response = client.get(f"/api/bookings{query}")

    assert response.status_code == 422
    assert response.json() == {
        "code": "VALIDATION_ERROR",
        "message": "Проверьте введённые данные",
        "fieldErrors": [
            {
                "field": "scope",
                "code": code,
                "message": message,
            }
        ],
    }


def test_list_upcoming_bookings_filters_sorts_and_returns_full_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "calendar_api.main.current_time",
        lambda: datetime.fromisoformat("2026-03-27T12:00:00+03:00"),
    )
    add_booking(
        "tomorrow",
        1,
        "Мария Волкова",
        "maria@example.com",
        "2026-03-28T09:00:00+03:00",
        "2026-03-28T10:00:00+03:00",
    )
    add_booking(
        "current",
        0,
        "Анна Смирнова",
        "anna@example.com",
        "2026-03-27T11:30:00+03:00",
        "2026-03-27T12:30:00+03:00",
    )
    add_booking(
        "later",
        2,
        "Игорь Петров",
        "igor@example.com",
        "2026-03-27T14:00:00+03:00",
        "2026-03-27T15:30:00+03:00",
    )
    add_booking(
        "ended-at-now",
        1,
        "Завершённый звонок",
        "ended@example.com",
        "2026-03-27T11:00:00+03:00",
        "2026-03-27T12:00:00+03:00",
    )
    add_booking(
        "past",
        0,
        "Прошедший звонок",
        "past@example.com",
        "2026-03-26T11:00:00+03:00",
        "2026-03-26T11:30:00+03:00",
    )

    response = client.get("/api/bookings?scope=upcoming")

    assert response.status_code == 200
    bookings = response.json()
    assert [booking["id"] for booking in bookings] == ["current", "later", "tomorrow"]
    assert bookings[0] == {
        "id": "current",
        "guestName": "Анна Смирнова",
        "guestEmail": "anna@example.com",
        "startsAt": "2026-03-27T11:30:00+03:00",
        "endsAt": "2026-03-27T12:30:00+03:00",
        "eventType": {
            "id": EVENT_TYPES[0].id,
            "name": "Знакомство",
            "description": (
                "Короткий звонок, чтобы познакомиться, обсудить задачу "
                "и определить следующие шаги"
            ),
            "durationMinutes": 30,
        },
    }
    assert all(
        set(booking)
        == {
            "id",
            "guestName",
            "guestEmail",
            "startsAt",
            "endsAt",
            "eventType",
        }
        for booking in bookings
    )


def test_list_upcoming_bookings_returns_empty_array_when_nothing_remains(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "calendar_api.main.current_time",
        lambda: datetime.fromisoformat("2026-03-27T12:00:00+03:00"),
    )
    add_booking(
        "ended",
        0,
        "Завершённый звонок",
        "ended@example.com",
        "2026-03-27T11:00:00+03:00",
        "2026-03-27T12:00:00+03:00",
    )

    response = client.get("/api/bookings?scope=upcoming")

    assert response.status_code == 200
    assert response.json() == []

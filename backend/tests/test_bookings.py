from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

import calendar_api.clock as clock
from calendar_api.main import BOOKINGS, EVENT_TYPES, Booking, app

client = TestClient(app)
MOSCOW = timezone(timedelta(hours=3), "Europe/Moscow")


def booking_payload() -> dict[str, str]:
    event_type = client.get("/api/event-types").json()[1]
    tomorrow = datetime.now(MOSCOW).date() + timedelta(days=1)
    return {
        "eventTypeId": event_type["id"],
        "startsAt": f"{tomorrow.isoformat()}T09:00+03:00",
        "guestName": "  Иван Петров  ",
        "guestEmail": "  ivan@example.com  ",
    }


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


def test_create_booking_computes_end_and_returns_nested_event_type() -> None:
    payload = booking_payload()

    response = client.post(
        "/api/bookings",
        json=payload,
        headers={"Idempotency-Key": str(uuid4())},
    )

    assert response.status_code == 201
    booking = response.json()
    assert str(UUID(booking["id"])) == booking["id"]
    assert booking["guestName"] == "Иван Петров"
    assert booking["guestEmail"] == "ivan@example.com"
    assert booking["startsAt"] == payload["startsAt"]
    assert booking["endsAt"] == payload["startsAt"].replace("09:00", "10:00")
    assert booking["eventType"]["id"] == payload["eventTypeId"]
    assert booking["eventType"]["durationMinutes"] == 60


def test_overlapping_booking_returns_conflict_without_creating_record() -> None:
    payload = booking_payload()
    first = client.post(
        "/api/bookings",
        json=payload,
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert first.status_code == 201
    other_type = client.get("/api/event-types").json()[2]
    overlapping = {
        **payload,
        "eventTypeId": other_type["id"],
        "startsAt": payload["startsAt"].replace("09:00", "09:30"),
    }

    response = client.post(
        "/api/bookings",
        json=overlapping,
        headers={"Idempotency-Key": str(uuid4())},
    )

    assert response.status_code == 409
    assert response.json() == {
        "code": "SLOT_CONFLICT",
        "message": "Это время уже занято",
        "fieldErrors": [],
    }
    assert len(client.get("/api/bookings?scope=upcoming").json()) == 1


def test_idempotent_retry_returns_original_booking_without_duplicate() -> None:
    key = str(uuid4())
    payload = booking_payload()

    first = client.post("/api/bookings", json=payload, headers={"Idempotency-Key": key})
    repeated = client.post(
        "/api/bookings",
        json={**payload, "guestName": "Иван Петров", "guestEmail": "ivan@example.com"},
        headers={"Idempotency-Key": key.upper()},
    )

    assert first.status_code == 201
    assert repeated.status_code == 201
    assert repeated.json() == first.json()
    assert len(client.get("/api/bookings?scope=upcoming").json()) == 1


def test_create_booking_returns_all_field_errors_in_contract_order() -> None:
    response = client.post(
        "/api/bookings",
        json={
            "eventTypeId": None,
            "startsAt": None,
            "guestName": "Иван" + "\n" + "Петров",
            "guestEmail": "invalid",
            "unexpected": True,
        },
        headers={"Idempotency-Key": str(uuid4())},
    )

    assert response.status_code == 422
    assert response.json() == {
        "code": "VALIDATION_ERROR",
        "message": "Проверьте введённые данные",
        "fieldErrors": [
            {
                "field": "eventTypeId",
                "code": "REQUIRED",
                "message": "Выберите тип события",
            },
            {"field": "startsAt", "code": "REQUIRED", "message": "Укажите время"},
            {
                "field": "guestName",
                "code": "NOT_SINGLE_LINE",
                "message": "Имя должно быть одной строкой",
            },
            {
                "field": "guestEmail",
                "code": "INVALID_EMAIL",
                "message": "Введите корректный email",
            },
            {
                "field": "unexpected",
                "code": "UNKNOWN_FIELD",
                "message": "Неизвестное поле",
            },
        ],
    }
    assert client.get("/api/bookings?scope=upcoming").json() == []


@pytest.mark.parametrize("key", [None, "not-a-uuid"])
def test_create_booking_requires_uuid_idempotency_key(key: str | None) -> None:
    headers = {} if key is None else {"Idempotency-Key": key}

    response = client.post("/api/bookings", json=booking_payload(), headers=headers)

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["fieldErrors"] == [
        {
            "field": "Idempotency-Key",
            "code": "REQUIRED" if key is None else "INVALID_IDEMPOTENCY_KEY",
            "message": (
                "Укажите ключ идемпотентности"
                if key is None
                else "Ключ идемпотентности должен быть UUID"
            ),
        }
    ]


def test_create_booking_rejects_malformed_json_without_pinning_key() -> None:
    key = str(uuid4())
    malformed = client.post(
        "/api/bookings",
        content="{",
        headers={"Content-Type": "application/json", "Idempotency-Key": key},
    )

    assert malformed.status_code == 400
    assert malformed.json() == {
        "code": "INVALID_JSON",
        "message": "Некорректное тело запроса",
        "fieldErrors": [],
    }

    valid_retry = client.post(
        "/api/bookings", json=booking_payload(), headers={"Idempotency-Key": key}
    )
    assert valid_retry.status_code == 201


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("eventTypeId", 123, "INVALID_TYPE"),
        ("startsAt", 123, "INVALID_TYPE"),
        ("startsAt", "2026-01-01T09:00:00+03:00", "INVALID_DATETIME"),
        ("startsAt", "2026-01-01T09:00:00.123+03:00", "INVALID_DATETIME"),
        ("startsAt", "2026-01-01T09:00+00:00", "INVALID_DATETIME"),
        ("startsAt", "2026-01-01T09:00Z", "INVALID_DATETIME"),
        ("guestName", 123, "INVALID_TYPE"),
        ("guestName", "   ", "REQUIRED"),
        ("guestName", "и" * 101, "TOO_LONG"),
        ("guestEmail", 123, "INVALID_TYPE"),
        ("guestEmail", "   ", "REQUIRED"),
        ("guestEmail", "a@b@c", "INVALID_EMAIL"),
        ("guestEmail", "a b@example.com", "INVALID_EMAIL"),
        ("guestEmail", "@example.com", "INVALID_EMAIL"),
        ("guestEmail", "a@b", None),
        ("guestEmail", f"{'a' * 247}@test.ru", "TOO_LONG"),
    ],
)
def test_create_booking_validates_each_field(
    field: str, value: object, code: str | None
) -> None:
    payload = {**booking_payload(), field: value}

    response = client.post(
        "/api/bookings", json=payload, headers={"Idempotency-Key": str(uuid4())}
    )

    if code is None:
        assert response.status_code == 201
        assert response.json()["guestEmail"] == "a@b"
        return
    assert response.status_code == 422
    field_errors = response.json()["fieldErrors"]
    assert len(field_errors) == 1
    assert field_errors[0]["field"] == field
    assert field_errors[0]["code"] == code
    assert field_errors[0]["message"]


@pytest.mark.parametrize("control", ["\x00", "\x1f", "\x7f", "\x80", "\x9f"])
def test_create_booking_rejects_control_characters_in_guest_email(
    control: str,
) -> None:
    response = client.post(
        "/api/bookings",
        json={
            **booking_payload(),
            "guestEmail": f"guest{control}@example.com",
        },
        headers={"Idempotency-Key": str(uuid4())},
    )

    assert response.status_code == 422
    assert response.json()["fieldErrors"] == [
        {
            "field": "guestEmail",
            "code": "INVALID_EMAIL",
            "message": "Введите корректный email",
        }
    ]


@pytest.mark.parametrize("event_type_id", ["not-a-uuid", str(uuid4())])
def test_create_booking_returns_not_found_for_unknown_event_type(
    event_type_id: str,
) -> None:
    response = client.post(
        "/api/bookings",
        json={**booking_payload(), "eventTypeId": event_type_id},
        headers={"Idempotency-Key": str(uuid4())},
    )

    assert response.status_code == 404
    assert response.json() == {
        "code": "EVENT_TYPE_NOT_FOUND",
        "message": "Тип события не найден",
        "fieldErrors": [],
    }


@pytest.mark.parametrize(
    ("starts_at", "code"),
    [
        ("todayT09:00+03:00", "START_OUTSIDE_BOOKING_WINDOW"),
        ("afterWindowT09:00+03:00", "START_OUTSIDE_BOOKING_WINDOW"),
        ("tomorrowT09:15+03:00", "START_NOT_ON_GRID"),
        ("tomorrowT08:30+03:00", "OUTSIDE_BOOKING_HOURS"),
        ("tomorrowT17:30+03:00", "OUTSIDE_BOOKING_HOURS"),
    ],
)
def test_create_booking_validates_booking_time(starts_at: str, code: str) -> None:
    today = datetime.now(MOSCOW).date()
    dates = {
        "today": today,
        "afterWindow": today + timedelta(days=15),
        "tomorrow": today + timedelta(days=1),
    }
    prefix, time_part = starts_at.split("T", maxsplit=1)
    payload = {
        **booking_payload(),
        "startsAt": f"{dates[prefix].isoformat()}T{time_part}",
    }

    response = client.post(
        "/api/bookings", json=payload, headers={"Idempotency-Key": str(uuid4())}
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["fieldErrors"][0]["field"] == "startsAt"
    assert response.json()["fieldErrors"][0]["code"] == code
    assert client.get("/api/bookings?scope=upcoming").json() == []


def test_adjacent_half_open_intervals_are_allowed() -> None:
    payload = booking_payload()
    first = client.post(
        "/api/bookings", json=payload, headers={"Idempotency-Key": str(uuid4())}
    )
    adjacent = client.post(
        "/api/bookings",
        json={**payload, "startsAt": payload["startsAt"].replace("09:00", "10:00")},
        headers={"Idempotency-Key": str(uuid4())},
    )

    assert first.status_code == 201
    assert adjacent.status_code == 201
    assert len(client.get("/api/bookings?scope=upcoming").json()) == 2


def test_idempotent_retry_replays_slot_conflict() -> None:
    payload = booking_payload()
    occupied = client.post(
        "/api/bookings", json=payload, headers={"Idempotency-Key": str(uuid4())}
    )
    assert occupied.status_code == 201
    key = str(uuid4())

    first = client.post("/api/bookings", json=payload, headers={"Idempotency-Key": key})
    repeated = client.post(
        "/api/bookings", json=payload, headers={"Idempotency-Key": key}
    )

    assert first.status_code == 409
    assert first.json()["code"] == "SLOT_CONFLICT"
    assert repeated.status_code == 409
    assert repeated.json() == first.json()
    assert len(client.get("/api/bookings?scope=upcoming").json()) == 1


@pytest.mark.parametrize("change", ["data", "fields"])
def test_pinned_idempotency_key_rejects_changed_request(change: str) -> None:
    key = str(uuid4())
    payload = booking_payload()
    created = client.post(
        "/api/bookings", json=payload, headers={"Idempotency-Key": key}
    )
    assert created.status_code == 201
    changed = (
        {**payload, "guestName": "Другой гость"}
        if change == "data"
        else {**payload, "unexpected": "value"}
    )

    response = client.post(
        "/api/bookings", json=changed, headers={"Idempotency-Key": key}
    )

    assert response.status_code == 409
    assert response.json() == {
        "code": "IDEMPOTENCY_KEY_REUSED",
        "message": (
            "Данные изменились после попытки отправки. Начните бронирование заново"
        ),
        "fieldErrors": [],
    }
    assert len(client.get("/api/bookings?scope=upcoming").json()) == 1


@pytest.mark.parametrize("initial_status", [404, 422])
def test_validation_and_not_found_errors_do_not_pin_idempotency_key(
    initial_status: int,
) -> None:
    key = str(uuid4())
    payload = booking_payload()
    initial_payload = (
        {**payload, "eventTypeId": str(uuid4())}
        if initial_status == 404
        else {**payload, "guestEmail": "invalid"}
    )
    initial = client.post(
        "/api/bookings", json=initial_payload, headers={"Idempotency-Key": key}
    )
    assert initial.status_code == initial_status

    retry = client.post("/api/bookings", json=payload, headers={"Idempotency-Key": key})

    assert retry.status_code == 201


def test_successful_retry_bypasses_expired_booking_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        clock,
        "moscow_now",
        lambda: datetime(2026, 2, 1, 12, 0, tzinfo=MOSCOW),
    )
    event_type = client.get("/api/event-types").json()[0]
    payload = {
        "eventTypeId": event_type["id"],
        "startsAt": "2026-02-02T09:00+03:00",
        "guestName": "Иван",
        "guestEmail": "ivan@example.com",
    }
    key = str(uuid4())
    created = client.post(
        "/api/bookings", json=payload, headers={"Idempotency-Key": key}
    )
    assert created.status_code == 201
    monkeypatch.setattr(
        clock,
        "moscow_now",
        lambda: datetime(2026, 3, 1, 12, 0, tzinfo=MOSCOW),
    )

    repeated = client.post(
        "/api/bookings", json=payload, headers={"Idempotency-Key": key}
    )

    assert repeated.status_code == 201
    assert repeated.json() == created.json()


def test_concurrent_overlapping_requests_create_only_one_booking() -> None:
    payload = booking_payload()
    other_type = client.get("/api/event-types").json()[2]
    requests = [
        (payload, str(uuid4())),
        (
            {
                **payload,
                "eventTypeId": other_type["id"],
                "startsAt": payload["startsAt"].replace("09:00", "09:30"),
            },
            str(uuid4()),
        ),
    ]

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(
                lambda item: client.post(
                    "/api/bookings",
                    json=item[0],
                    headers={"Idempotency-Key": item[1]},
                ),
                requests,
            )
        )

    assert sorted(response.status_code for response in responses) == [201, 409]
    assert len(client.get("/api/bookings?scope=upcoming").json()) == 1


def test_concurrent_retries_with_one_key_return_same_result() -> None:
    payload = booking_payload()
    key = str(uuid4())

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(
                lambda _: client.post(
                    "/api/bookings",
                    json=payload,
                    headers={"Idempotency-Key": key},
                ),
                range(2),
            )
        )

    assert [response.status_code for response in responses] == [201, 201]
    assert responses[0].json() == responses[1].json()
    assert len(client.get("/api/bookings?scope=upcoming").json()) == 1


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
        "calendar_api.clock.moscow_now",
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
        "startsAt": "2026-03-27T11:30+03:00",
        "endsAt": "2026-03-27T12:30+03:00",
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
        "calendar_api.clock.moscow_now",
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

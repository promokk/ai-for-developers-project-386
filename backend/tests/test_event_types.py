from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from calendar_api.main import app

client = TestClient(app)


def test_list_event_types_returns_seed_types_in_creation_order() -> None:
    response = client.get("/api/event-types")

    assert response.status_code == 200
    event_types = response.json()
    assert [
        (event_type["name"], event_type["description"], event_type["durationMinutes"])
        for event_type in event_types
    ] == [
        (
            "Знакомство",
            "Короткий звонок, чтобы познакомиться, обсудить задачу "
            "и определить следующие шаги",
            30,
        ),
        (
            "Консультация",
            "Подробное обсуждение вашего вопроса, разбор возможных решений "
            "и следующих шагов",
            60,
        ),
        (
            "Глубокий разбор",
            "Детальный разбор сложной задачи и составление конкретного плана действий",
            90,
        ),
    ]
    assert all(
        set(event_type) == {"id", "name", "description", "durationMinutes"}
        for event_type in event_types
    )
    assert len({event_type["id"] for event_type in event_types}) == len(event_types)
    assert all(
        str(UUID(event_type["id"])) == event_type["id"] for event_type in event_types
    )


def test_create_event_type_normalizes_and_appends_type() -> None:
    before = client.get("/api/event-types").json()

    response = client.post(
        "/api/event-types",
        json={
            "name": "  Стратегическая сессия  ",
            "description": "  Разберём цели\nи составим план.  ",
            "durationMinutes": 120,
        },
    )

    assert response.status_code == 201
    created = response.json()
    assert created["name"] == "Стратегическая сессия"
    assert created["description"] == "Разберём цели\nи составим план."
    assert created["durationMinutes"] == 120
    assert str(UUID(created["id"])) == created["id"]
    assert set(created) == {"id", "name", "description", "durationMinutes"}
    assert client.get("/api/event-types").json() == [*before, created]


@pytest.mark.parametrize("content", ["{", b'{"name":"\xff"}'])
def test_create_event_type_rejects_invalid_json(content: str | bytes) -> None:
    response = client.post(
        "/api/event-types",
        content=content,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400
    assert response.json() == {
        "code": "INVALID_JSON",
        "message": "Некорректное тело запроса",
        "fieldErrors": [],
    }


def test_create_event_type_returns_all_field_errors_in_contract_order() -> None:
    before = client.get("/api/event-types").json()

    response = client.post(
        "/api/event-types",
        json={
            "name": "first line\nsecond line",
            "description": "д" * 501,
            "durationMinutes": 45,
            "extra": True,
            "another": "значение",
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "code": "VALIDATION_ERROR",
        "message": "Проверьте введённые данные",
        "fieldErrors": [
            {
                "field": "name",
                "code": "NOT_SINGLE_LINE",
                "message": "Название должно быть одной строкой",
            },
            {
                "field": "description",
                "code": "TOO_LONG",
                "message": "Описание не должно превышать 500 символов",
            },
            {
                "field": "durationMinutes",
                "code": "INVALID_DURATION",
                "message": "Выберите длительность: 30, 60, 90 или 120 минут",
            },
            {"field": "extra", "code": "UNKNOWN_FIELD", "message": "Неизвестное поле"},
            {
                "field": "another",
                "code": "UNKNOWN_FIELD",
                "message": "Неизвестное поле",
            },
        ],
    }
    assert client.get("/api/event-types").json() == before


@pytest.mark.parametrize(
    ("payload", "field", "code", "message"),
    [
        ({}, "name", "REQUIRED", "Введите название"),
        ({"name": None}, "name", "REQUIRED", "Введите название"),
        ({"name": "  "}, "name", "REQUIRED", "Введите название"),
        ({"name": 42}, "name", "INVALID_TYPE", "Название должно быть строкой"),
        (
            {"name": f"  {'н' * 101}  "},
            "name",
            "TOO_LONG",
            "Название не должно превышать 100 символов",
        ),
        (
            {"description": 42},
            "description",
            "INVALID_TYPE",
            "Описание должно быть строкой",
        ),
        (
            {"description": f"  {'д' * 501}  "},
            "description",
            "TOO_LONG",
            "Описание не должно превышать 500 символов",
        ),
        (
            {},
            "durationMinutes",
            "REQUIRED",
            "Выберите длительность: 30, 60, 90 или 120 минут",
        ),
        (
            {"durationMinutes": None},
            "durationMinutes",
            "REQUIRED",
            "Выберите длительность: 30, 60, 90 или 120 минут",
        ),
        *[
            (
                {"durationMinutes": value},
                "durationMinutes",
                "INVALID_DURATION",
                "Выберите длительность: 30, 60, 90 или 120 минут",
            )
            for value in (0, 29, 31, 45, 121, True, 30.0, "30")
        ],
    ],
)
def test_create_event_type_validates_each_field(
    payload: dict[str, object], field: str, code: str, message: str
) -> None:
    body = {"name": "Новый тип", "durationMinutes": 30, **payload}
    if not payload:
        body.pop(field)

    response = client.post("/api/event-types", json=body)

    assert response.status_code == 422
    assert response.json() == {
        "code": "VALIDATION_ERROR",
        "message": "Проверьте введённые данные",
        "fieldErrors": [
            {"field": field, "code": code, "message": message},
        ],
    }


@pytest.mark.parametrize("description", [None, "", "   "])
def test_create_event_type_stores_empty_description_as_null(
    description: str | None,
) -> None:
    response = client.post(
        "/api/event-types",
        json={
            "name": "Без описания",
            "description": description,
            "durationMinutes": 60,
        },
    )

    assert response.status_code == 201
    assert response.json()["description"] is None


def test_create_event_type_defaults_omitted_description_to_null() -> None:
    response = client.post(
        "/api/event-types",
        json={"name": "Без описания", "durationMinutes": 30},
    )

    assert response.status_code == 201
    assert response.json()["description"] is None


def test_create_event_type_allows_duplicate_unicode_names_and_boundaries() -> None:
    name = "  " + "ё" * 100 + "  "
    description = "  " + "ж" * 500 + "  "

    first = client.post(
        "/api/event-types",
        json={"name": name, "description": description, "durationMinutes": 90},
    )
    second = client.post(
        "/api/event-types",
        json={"name": name, "description": description, "durationMinutes": 90},
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["name"] == second.json()["name"] == "ё" * 100
    assert first.json()["description"] == second.json()["description"] == "ж" * 500
    assert first.json()["id"] != second.json()["id"]

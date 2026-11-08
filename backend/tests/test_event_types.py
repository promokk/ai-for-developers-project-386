from uuid import UUID

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

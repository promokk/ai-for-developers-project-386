from fastapi.testclient import TestClient

from calendar_api.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_booking_with_legacy_contract() -> None:
    payload = {
        "name": "Демо-звонок",
        "startsAt": "2026-11-10T10:00:00Z",
        "endsAt": "2026-11-10T10:30:00Z",
    }
    created = client.post("/api/bookings", json=payload)

    assert created.status_code == 201
    assert created.json()["name"] == "Демо-звонок"

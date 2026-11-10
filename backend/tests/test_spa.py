from pathlib import Path

from fastapi.testclient import TestClient

from calendar_api.main import create_app


def test_client_route_returns_spa_index(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<html>Calendar</html>", encoding="utf-8")
    client = TestClient(create_app(static_dir=tmp_path))

    response = client.get("/book")

    assert response.status_code == 200
    assert response.text == "<html>Calendar</html>"


def test_static_asset_is_served(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<html>Calendar</html>", encoding="utf-8")
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "main.js").write_text("console.log('Calendar')", encoding="utf-8")
    client = TestClient(create_app(static_dir=tmp_path))

    response = client.get("/assets/main.js")

    assert response.status_code == 200
    assert response.text == "console.log('Calendar')"


def test_unknown_api_route_does_not_return_spa_index(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<html>Calendar</html>", encoding="utf-8")
    client = TestClient(create_app(static_dir=tmp_path))

    response = client.get("/api/unknown")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}

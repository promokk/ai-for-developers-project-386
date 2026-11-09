from pathlib import Path

import yaml

from calendar_api.main import app

OPENAPI_SPEC = Path(__file__).parents[2] / "contracts" / "openapi" / "openapi.yaml"


def test_app_matches_contract() -> None:
    spec = yaml.safe_load(OPENAPI_SPEC.read_text(encoding="utf-8"))
    generated = app.openapi()

    for path, methods in spec["paths"].items():
        assert path in generated["paths"], f"путь {path} отсутствует в приложении"
        for method in methods:
            assert method in generated["paths"][path], (
                f"метод {method.upper()} {path} отсутствует в приложении"
            )

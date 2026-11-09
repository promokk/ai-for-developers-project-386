from fastapi.responses import JSONResponse

FieldError = dict[str, str]


def api_error(
    status_code: int,
    code: str,
    message: str,
    field_errors: list[FieldError] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "message": message,
            "fieldErrors": field_errors or [],
        },
    )


def field_error(field: str, code: str, message: str) -> FieldError:
    return {"field": field, "code": code, "message": message}

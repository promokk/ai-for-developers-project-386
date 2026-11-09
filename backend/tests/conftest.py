from collections.abc import Iterator

import pytest

import calendar_api.main as main


@pytest.fixture(autouse=True)
def clear_bookings() -> Iterator[None]:
    main.BOOKINGS.clear()
    main.IDEMPOTENCY_RESULTS.clear()
    yield
    main.BOOKINGS.clear()
    main.IDEMPOTENCY_RESULTS.clear()

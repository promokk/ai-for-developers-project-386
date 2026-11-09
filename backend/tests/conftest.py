from collections.abc import Iterator

import pytest

import calendar_api.main as main


@pytest.fixture(autouse=True)
def reset_state() -> Iterator[None]:
    event_types = main.EVENT_TYPES.copy()
    main.BOOKINGS.clear()
    main.IDEMPOTENCY_RESULTS.clear()
    yield
    main.BOOKINGS.clear()
    main.IDEMPOTENCY_RESULTS.clear()
    main.EVENT_TYPES[:] = event_types

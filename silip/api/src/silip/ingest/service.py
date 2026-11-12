"""Validate at the boundary, then store."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from silip.ingest.domain import InvalidReadingError, ReadingSink
from silip_ml.readings.domain import Reading


def ingest(payload: dict[str, Any], sink: ReadingSink) -> Reading:
    """Validate one MQTT payload and write it.

    Raises:
        InvalidReadingError: with field names only (never the values, which may identify a home).
    """
    try:
        reading = Reading.model_validate(payload)
    except ValidationError as error:
        fields = sorted({".".join(map(str, e["loc"])) for e in error.errors()})
        raise InvalidReadingError(f"invalid fields: {', '.join(fields)}") from None
    sink.write(reading)
    return reading

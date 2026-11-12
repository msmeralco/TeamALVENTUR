"""The port where validated readings are stored."""

from __future__ import annotations

from typing import Protocol

from silip_ml.readings.domain import Reading


class InvalidReadingError(ValueError):
    """The payload does not match `schemas/reading.json`."""


class ReadingSink(Protocol):
    def write(self, reading: Reading) -> None: ...


class DeviceAuthenticationError(ValueError):
    """Missing or invalid device credential."""

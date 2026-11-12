"""Device-key authenticated HTTPS ingestion, served by the existing API Lambda."""

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Response

from silip.ingest.adapters import HttpReadingReceiver
from silip.ingest.domain import DeviceAuthenticationError, InvalidReadingError
from silip.shared.config import Settings
from silip.shared.db import connect
from silip_ml.readings.domain import DeviceReading

router = APIRouter(prefix="/api/v1/devices", tags=["device-readings"])


@router.post("/{clamp_id}/readings", status_code=204)
def receive_reading(
    clamp_id: str,
    payload: DeviceReading,
    settings: Settings,
    device_key: Annotated[str | None, Header(alias="X-Device-Key", max_length=256)] = None,
) -> Response:
    if not device_key:
        raise HTTPException(401, "Device key required")
    try:
        HttpReadingReceiver(lambda: connect(settings)).receive(clamp_id, device_key, payload)
    except DeviceAuthenticationError:
        raise HTTPException(401, "Invalid device key") from None
    except InvalidReadingError as error:
        raise HTTPException(422, str(error)) from None
    return Response(status_code=204)

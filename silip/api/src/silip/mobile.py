"""Unauthenticated, allowlisted mobile PoC read API."""

import os

from fastapi import FastAPI, HTTPException, Response
from mangum import Mangum

from silip.devices.adapters import NeonDeviceRegistry
from silip.devices.domain import DemoDeviceUsage
from silip.shared.config import Settings
from silip.shared.db import connect

app = FastAPI(
    title="SILIP Mobile PoC API",
    version="0.1.0",
    description="Read-only usage summary for the allowlisted PoC device.",
)

# Keep the endpoint limited to explicitly enabled demo IDs while the app has no sign-in.
PUBLIC_POC_DEVICE_IDS = frozenset(
    device_id.strip()
    for device_id in os.environ.get("MOBILE_POC_DEVICE_IDS", "").split(",")
    if device_id.strip()
)


@app.get(
    "/mobile-api/v1/devices/{clamp_id}/usage",
    response_model=DemoDeviceUsage,
)
def device_usage(clamp_id: str, settings: Settings, response: Response) -> DemoDeviceUsage:
    if clamp_id not in PUBLIC_POC_DEVICE_IDS:
        raise HTTPException(404, "Demo device not found")
    response.headers["Cache-Control"] = "no-store"
    usage = NeonDeviceRegistry(lambda: connect(settings)).demo_usage(clamp_id)
    if usage is None:
        raise HTTPException(404, "Demo device not found")
    return usage


handler = Mangum(app, lifespan="off")

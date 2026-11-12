"""Engineer-only device installation and transformer telemetry endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response

from silip.devices import service
from silip.devices.adapters import NeonDeviceRegistry
from silip.devices.domain import (
    Device,
    DeviceKey,
    DeviceRegistration,
    DeviceSetup,
    Installation,
    RegistryError,
    TransformerOption,
    TransformerRegistration,
    TransformerTelemetry,
)
from silip.shared.auth.api import Engineer
from silip.shared.config import Settings
from silip.shared.db import connect

router = APIRouter(prefix="/api/v1/devices", tags=["devices"])


def registry(settings: Settings) -> NeonDeviceRegistry:
    return NeonDeviceRegistry(lambda: connect(settings))


Registry = Annotated[NeonDeviceRegistry, Depends(registry)]


@router.get("")
def devices(store: Registry, _: Engineer) -> list[Device]:
    return store.devices()


@router.get("/transformers")
def transformers(store: Registry, _: Engineer) -> list[TransformerOption]:
    return store.transformers()


@router.post("/transformers", status_code=201)
def add_transformer(
    request: TransformerRegistration, store: Registry, _: Engineer
) -> TransformerOption:
    try:
        return store.add_transformer(request)
    except RegistryError as error:
        raise HTTPException(409, str(error)) from None


@router.get("/transformers/{transformer_id}/telemetry")
def telemetry(transformer_id: str, store: Registry, _: Engineer) -> TransformerTelemetry:
    try:
        return store.aggregate(transformer_id)
    except RegistryError as error:
        raise HTTPException(404, str(error)) from None


@router.post("", status_code=201)
def register(
    request: DeviceRegistration, store: Registry, _: Engineer, response: Response
) -> DeviceSetup:
    response.headers["Cache-Control"] = "no-store"
    try:
        return service.register(request, store)
    except RegistryError as error:
        raise HTTPException(409, str(error)) from None


@router.put("/{clamp_id}/installation")
def assign(clamp_id: str, request: Installation, store: Registry, _: Engineer) -> Device:
    try:
        return store.assign(clamp_id, request)
    except RegistryError as error:
        raise HTTPException(409, str(error)) from None


@router.post("/{clamp_id}/key")
def replace_key(clamp_id: str, store: Registry, _: Engineer, response: Response) -> DeviceKey:
    response.headers["Cache-Control"] = "no-store"
    try:
        return store.replace_key(clamp_id)
    except RegistryError as error:
        raise HTTPException(404, str(error)) from None

"""Device installation contracts and the limited mobile PoC usage response."""

from datetime import datetime
from secrets import token_urlsafe
from typing import Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from silip_ml.core.privacy import sin_hash
from silip_ml.readings.domain import SIN_HASH_PATTERN


class DeviceRegistration(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    clamp_id: str = Field(
        default_factory=lambda: "silip-node-" + uuid4().hex[:12], pattern=r"^[a-zA-Z0-9:_-]{1,128}$"
    )
    sin_hash: str = Field(
        default_factory=lambda: sin_hash(token_urlsafe(32), token_urlsafe(32)),
        pattern=SIN_HASH_PATTERN,
    )
    transformer_id: str = Field(min_length=1, max_length=32)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    location_label: str | None = Field(default=None, max_length=200)
    ct_model: str = Field(default="SCT-013-000", min_length=1, max_length=64)
    is_simulated: bool = False
    consent_confirmed: bool


class Installation(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    transformer_id: str = Field(min_length=1, max_length=32)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    location_label: str | None = Field(default=None, max_length=200)


class Device(BaseModel):
    clamp_id: str
    transformer_id: str
    lat: float | None
    lon: float | None
    location_label: str | None = None
    ct_model: str
    installed_at: datetime
    last_seen_at: datetime | None
    status: str
    is_simulated: bool

    device_key_set: bool = False


class DeviceSetup(Device):
    device_key: str = Field(repr=False)


class DeviceKey(BaseModel):
    device_key: str = Field(repr=False)


class TransformerOption(BaseModel):
    transformer_id: str
    lat: float
    lon: float
    is_simulated: bool


class TransformerRegistration(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    transformer_id: str = Field(min_length=1, max_length=32, pattern=r"^[a-zA-Z0-9:_-]{1,32}$")
    rated_kva: float = Field(gt=0, le=100_000)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    homes: int = Field(default=0, ge=0)
    coverage_pct: float = Field(default=0, ge=0, le=1)
    is_simulated: bool = False


class AggregatePoint(BaseModel):
    ts: datetime
    measured_kw: float
    energy_kwh: float
    homes_reporting: int
    is_simulated: bool


class TransformerTelemetry(BaseModel):
    transformer_id: str
    registered_homes: int
    points: list[AggregatePoint]


class DemoUsagePoint(BaseModel):
    ts: datetime
    kw: float


class DemoDeviceUsage(BaseModel):
    """Sanitized, public usage summary for the single PoC device."""

    clamp_id: str
    transformer_id: str
    last_seen_at: datetime | None
    total_kwh: float
    is_simulated: bool
    points: list[DemoUsagePoint]


class RegistryError(ValueError):
    """An installation violates the registry's constraints."""


class DeviceRegistry(Protocol):
    def devices(self) -> list[Device]: ...
    def transformers(self) -> list[TransformerOption]: ...
    def add_transformer(self, request: TransformerRegistration) -> TransformerOption: ...
    def register(self, request: DeviceRegistration) -> DeviceSetup: ...
    def assign(self, clamp_id: str, request: Installation) -> Device: ...
    def aggregate(self, transformer_id: str) -> TransformerTelemetry: ...

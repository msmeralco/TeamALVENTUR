"""Engineer-only dashboard summary: one row of what the area needs before the next peak."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from silip.dashboard.adapters import model_kept
from silip.dashboard.domain import (
    ACTIONS,
    TIERS,
    ClampSummary,
    DashboardSummary,
    ModelSummary,
    WeatherSummary,
    count,
)
from silip.shared.auth.api import Engineer
from silip.shared.config import Settings
from silip.shared.deps import Source
from silip.shared.geo import BoundingBox, parse_bbox, within
from silip.transformers.api import RESPONSES, Snapshot
from silip.transformers.service import risk_map
from silip.weather.api import Forecast, Now
from silip.weather.domain import SOURCE_LABELS
from silip.weather.service import cell_peaks, cells_for

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary, responses=RESPONSES)
def dashboard_summary(
    _: Engineer,
    snapshot: Snapshot,
    source: Source,
    settings: Settings,
    forecast: Forecast,
    now: Now,
    box: Annotated[BoundingBox | None, Depends(parse_bbox)],
) -> DashboardSummary:
    """Tiers and actions in view, weather freshness and the hottest hour ahead, clamps online,
    and which models scored it."""
    rows = risk_map(snapshot, source, box)
    healths = [row.clamp_health for row in rows if row.clamp_health is not None]
    in_view = within(snapshot.transformers, box)
    peaks = [
        peak
        for peak in cell_peaks(forecast, cells_for(in_view) if not in_view.empty else [], now)
        if peak.heat_index_max_c is not None
    ]
    hottest = max(peaks, key=lambda peak: peak.heat_index_max_c or 0.0, default=None)
    verdicts = [
        model_kept(settings.models_dir, task, name)
        for task, name in (
            ("forecaster", snapshot.forecaster),
            ("risk_scorer", snapshot.risk_scorer),
        )
        if name is not None
    ]
    known = [verdict for verdict in verdicts if verdict is not None]
    weather_simulated = forecast.is_simulated or settings.weather_source == "simulated"
    return DashboardSummary(
        as_of=snapshot.as_of.to_pydatetime(),
        scored_at=snapshot.scored_at,
        tiers=count([row.risk.tier for row in rows], TIERS),
        actions=count([row.action for row in rows if row.action is not None], ACTIONS),
        weather=WeatherSummary(
            issued_at=forecast.issued_at,
            status=forecast.status,
            source=SOURCE_LABELS[settings.weather_source],
            heat_index_max_c=None if hottest is None else hottest.heat_index_max_c,
            max_at=None if hottest is None else hottest.max_at,
        ),
        clamps=ClampSummary(
            installed=sum(health.clamps_installed for health in healths),
            online=sum(health.clamps_online for health in healths),
        ),
        model=ModelSummary(
            forecaster=snapshot.forecaster,
            risk_scorer=snapshot.risk_scorer,
            kept=all(known) if known else None,
        ),
        is_simulated=any(row.is_simulated for row in rows) or weather_simulated,
    )

"""Baseline: pin the outage at the first customer report (first last gasp if none)."""

from __future__ import annotations

import pandas as pd

from silip_ml.core.registry import register


@register("outage_locator", "nearest_report")
class NearestReport:
    """What a dispatcher does today: go where the first call came from."""

    def locate(self, signals: pd.DataFrame) -> pd.DataFrame:
        ordered = signals.assign(is_report=signals["kind"].eq("report")).sort_values(
            ["outage_id", "is_report", "ts"], ascending=[True, False, True]
        )
        first = ordered.groupby("outage_id", as_index=False).first()
        return first[["outage_id", "lat", "lon"]]

import pandas as pd

from silip.clamps import service
from silip.shared.readings.adapters import CLAMP_COLUMNS, SimulatedSource
from tests.api.helpers import auth

POINT_FIELDS = {
    "clamp_id",
    "transformer_id",
    "lat",
    "lon",
    "ct_model",
    "installed_at",
    "last_seen_at",
    "status",
    "is_simulated",
}
AS_OF = pd.Timestamp("2026-04-30 23:45", tz="Asia/Manila")


class _Clamps:
    """Fake DataSource with only the clamps table."""

    def __init__(self, frame: pd.DataFrame) -> None:
        self._frame = frame

    def clamps(self) -> pd.DataFrame:
        return self._frame


def _row(clamp_id: str, last_seen_at: pd.Timestamp | None, lat: float = 14.5) -> dict:
    return {
        "clamp_id": clamp_id,
        "transformer_id": "T-1",
        "lat": lat,
        "lon": 121.0,
        "ct_model": "SCT-013-000",
        "installed_at": AS_OF - pd.Timedelta(days=30),
        "last_seen_at": last_seen_at,
        "is_simulated": True,
    }


def test_clamps_are_engineer_only(client):
    assert client.get("/api/v1/clamps").status_code == 401
    assert client.get("/api/v1/clamps", headers=auth("household-token")).status_code == 403


def test_engineer_sees_devices_not_households(client, sim_dir):
    response = client.get("/api/v1/clamps", headers=auth("engineer-token"))
    assert response.status_code == 200
    body = response.json()
    assert len(body["clamps"]) == len(SimulatedSource(sim_dir).clamps()) > 0
    assert body["is_simulated"] and body["offline_after_min"] == 60
    assert all(set(item) == POINT_FIELDS for item in body["clamps"])
    assert all(item["is_simulated"] for item in body["clamps"])
    keys = [(item["transformer_id"], item["clamp_id"]) for item in body["clamps"]]
    assert keys == sorted(keys)
    assert "sin_hash" not in response.text and "power_kw" not in response.text


def test_bbox_filters_and_rejects_bad_input(client):
    empty = client.get("/api/v1/clamps?bbox=0,0,1,1", headers=auth("engineer-token"))
    assert empty.json()["clamps"] == []
    bad = client.get("/api/v1/clamps?bbox=1,2,3", headers=auth("engineer-token"))
    assert bad.status_code == 422


def test_offline_after_an_hour_silent_on_the_data_clock():
    frame = pd.DataFrame(
        [
            _row("recent", AS_OF),
            _row("stale", AS_OF - pd.Timedelta(minutes=61)),
            _row("never", None),
        ],
        columns=CLAMP_COLUMNS,
    )
    result = service.clamp_map(_Clamps(frame), None)  # pyright: ignore[reportArgumentType]
    assert result.as_of == AS_OF
    assert {p.clamp_id: p.status for p in result.clamps} == {
        "recent": "online",
        "stale": "offline",
        "never": "offline",
    }
    assert service.status(AS_OF - service.OFFLINE_AFTER, AS_OF) == "online"


def test_no_clamps_means_no_clock():
    result = service.clamp_map(_Clamps(pd.DataFrame(columns=CLAMP_COLUMNS)), None)  # pyright: ignore[reportArgumentType]
    assert result.as_of is None and result.clamps == [] and not result.is_simulated

from tests.api.helpers import auth


def test_outage_list_is_public_and_coarse(client, dataset):
    body = client.get("/api/v1/outages?status=restored").json()
    assert len(body) > 0
    for outage in body:
        assert outage["is_simulated"]
        assert round(outage["area_lat"], 3) == outage["area_lat"]  # area only, not the exact pin
        assert "transformer_id" not in outage and "pin_lat" not in outage
        assert outage["eta_p10_min"] <= outage["eta_p50_min"] <= outage["eta_p90_min"]


def test_outage_detail_is_engineer_only(client, dataset):
    outage_id = dataset.outages["outage_id"].iloc[0]
    assert client.get(f"/api/v1/outages/{outage_id}").status_code == 401
    detail = client.get(f"/api/v1/outages/{outage_id}", headers=auth("engineer-token")).json()
    assert detail["last_gasp_count"] + detail["report_count"] > 0
    assert client.get("/api/v1/outages/O-NOPE", headers=auth("engineer-token")).status_code == 404

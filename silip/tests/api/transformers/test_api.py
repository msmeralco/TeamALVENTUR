from tests.api.helpers import auth


def test_risk_map_is_engineer_only(client):
    assert client.get("/api/v1/transformers").status_code == 401
    assert client.get("/api/v1/transformers", headers=auth("household-token")).status_code == 403


def test_risk_map_lists_every_transformer_critical_first(client, dataset):
    body = client.get("/api/v1/transformers", headers=auth("engineer-token")).json()
    assert len(body) == len(dataset.transformers)
    order = {"Critical": 0, "Watch": 1, "OK": 2}
    tiers = [order[item["risk"]["tier"]] for item in body]
    assert tiers == sorted(tiers)
    assert all(item["is_simulated"] and item["risk"]["is_simulated"] for item in body)


def test_bbox_filters_and_rejects_bad_input(client):
    empty = client.get("/api/v1/transformers?bbox=0,0,1,1", headers=auth("engineer-token"))
    assert empty.json() == []
    bad = client.get("/api/v1/transformers?bbox=1,2,3", headers=auth("engineer-token"))
    assert bad.status_code == 422


def test_card_has_history_and_forecast(client, dataset):
    transformer_id = dataset.transformers["transformer_id"].iloc[0]
    card = client.get(
        f"/api/v1/transformers/{transformer_id}", headers=auth("engineer-token")
    ).json()
    kinds = {point["is_forecast"] for point in card["load"]}
    assert kinds == {True, False}
    assert (
        client.get("/api/v1/transformers/T-NOPE", headers=auth("engineer-token")).status_code == 404
    )

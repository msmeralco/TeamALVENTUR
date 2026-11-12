import pytest

from silip_ml.core.registry import create, names
from silip_ml.readings.domain import STEPS_PER_DAY


@pytest.mark.parametrize("name", names("forecaster"))
def test_forecaster_contract(dataset, name):
    """Every forecaster returns one row per transformer per step, after the history ends."""
    forecaster = create("forecaster", name).fit(dataset.load)
    forecast = forecaster.predict(dataset.load, STEPS_PER_DAY)
    transformers = dataset.transformers["transformer_id"].nunique()
    assert len(forecast) == transformers * STEPS_PER_DAY
    assert forecast["ts"].min() > dataset.load["ts"].max()
    assert forecast["kw_pred"].notna().all()

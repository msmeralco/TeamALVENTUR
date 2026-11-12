"""Outage location and restoration ETA. Importing this package registers every strategy."""

from silip_ml.outages import dbscan, median_by_cause, nearest_report, quantile_lgbm  # noqa: F401

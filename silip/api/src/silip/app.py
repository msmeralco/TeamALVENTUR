"""Composition root: the FastAPI app and its Lambda handler.

uvicorn silip.app:app --reload           # local
python -m silip.app web/openapi.json     # export OpenAPI for the web client
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi import FastAPI
from mangum import Mangum

from silip.bench.api import router as bench_router
from silip.clamps.api import router as clamps_router
from silip.devices.api import router as devices_router
from silip.household.api import router as household_router
from silip.ingest.api import router as ingest_router
from silip.outages.api import router as outages_router
from silip.shared.auth.api import router as auth_router
from silip.shared.config import get_settings
from silip.transformers.api import router as transformers_router

# Fail at cold start, not on the first request, if AUTH_DISABLED=true is set inside Lambda.
get_settings()

app = FastAPI(
    title="SILIP API",
    version="0.1.0",
    description="Transformer risk, outages and household usage. Decision support only.",
)


@app.get("/api/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


for router in (
    auth_router,
    transformers_router,
    outages_router,
    household_router,
    clamps_router,
    devices_router,
    ingest_router,
    bench_router,
):
    app.include_router(router)

handler = Mangum(app, lifespan="off")


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "web/openapi.json")
    out.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")

"""Bench simulator: the rig without hardware, and the demo's fallback.

Sends what each clamp sends, one reading per house every SAMPLE_INTERVAL_S, through the same path
as the real devices: an HTTPS POST to /api/v1/devices/{clamp_id}/readings with the device key.
Every row is is_simulated=true.

    # live controls: type h (heat), e (EV), t (trip T1), r (restore), q (quit) + Enter,
    # or GET http://127.0.0.1:8765/?heat=on|off&ev=on|off&trip=on|off
    BENCH_DEVICE_KEY=... python -m silip.bench.sim --http https://<api-origin>
    python -m silip.bench.sim --script --stdout | python -m silip.ingest.local   # no API needed
    python -m silip.bench.sim --replay capture.jsonl --http https://<api-origin>
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import urllib.request
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import numpy as np

from silip.shared.bench import config

CONTROL_PORT = 8765
SECONDS_PER_HOUR = 3600
W_PER_KW = 1000
HTTP_TIMEOUT_S = 5
# The 2-minute story: (seconds from start, switch, on). Matches docs/demo/runbook.md.
SCRIPT: tuple[tuple[float, str, bool], ...] = (
    (20, "heat", True),
    (40, "ev", True),
    (95, "trip", True),
    (115, "trip", False),
    (125, "ev", False),
    (125, "heat", False),
)

# (clamp_id, payload) per house; one call per tick so a publisher can send them together.
Publish = Callable[[list[tuple[str, dict[str, Any]]]], None]


@dataclass
class Switches:
    heat: bool = False
    ev: bool = False
    trip: bool = False

    def set(self, name: str, on: bool) -> None:
        setattr(self, name, on)
        print(f"[sim] {name} {'on' if on else 'off'}", file=sys.stderr)


@dataclass
class Rig:
    """Resistive model: each home is a fixed resistance; each transformer is a source behind
    SERIES_OHMS, so its bus voltage sags as its homes draw more."""

    switches: Switches = field(default_factory=Switches)
    rng: np.random.Generator = field(default_factory=lambda: np.random.default_rng(7))
    flicker: dict[str, bool] = field(default_factory=dict)
    gasped: set[str] = field(default_factory=set)

    def demand_w(self, label: str) -> float:
        """What the home would draw at the nominal source voltage."""
        if self.rng.random() < config.FLICKER_CHANCE:
            self.flicker[label] = not self.flicker.get(label, False)
        watts = config.BASE_W + (config.FLICKER_W if self.flicker.get(label) else 0.0)
        if self.switches.heat:
            watts += config.HEAT_WAVE_W
        if self.switches.ev and label == config.EV_HOME:
            watts += config.EV_W
        return watts

    def step(self, now: datetime) -> Iterator[tuple[str, dict[str, Any]]]:
        """One (clamp_id, payload) per powered home, or one last gasp per home that just lost power."""
        demand = {home.label: self.demand_w(home.label) for home in config.HOMES}
        for transformer in config.TRANSFORMERS:
            homes = [h for h in config.HOMES if h.wired_transformer == transformer.transformer_id]
            ohms = {h.label: config.SOURCE_V**2 / demand[h.label] for h in homes}
            tripped = self.switches.trip and transformer.transformer_id == "BENCH-T1"
            parallel = 1 / sum(1 / r for r in ohms.values())
            bus_v = 0.0 if tripped else config.SOURCE_V * parallel / (parallel + config.SERIES_OHMS)
            for home in homes:
                if tripped and home.label in self.gasped:
                    continue  # said its last gasp; silent until power is back
                volts = max(
                    0.0,
                    bus_v * (1 - config.HOUSE_WIRE_OHMS / ohms[home.label])
                    + self.rng.normal(0, config.VOLTAGE_NOISE_V),
                )
                if tripped:
                    self.gasped.add(home.label)
                    volts = 0.0
                else:
                    self.gasped.discard(home.label)
                amps = volts / ohms[home.label]
                power_kw = volts * amps / W_PER_KW
                yield (
                    home.clamp_id,
                    {
                        # Identifiers the ingest path also accepts; the server owns the assignment,
                        # and the records put house 4 under T1.
                        "sin_hash": home.sin_hash,
                        "transformer_id": home.record_transformer,
                        "ts": now.isoformat(),
                        "voltage_v": round(volts, 4),
                        "current_a": round(amps, 5),
                        "power_kw": round(power_kw, 7),
                        "power_factor": 1.0,
                        "energy_kwh_interval": power_kw
                        * config.SAMPLE_INTERVAL_S
                        / SECONDS_PER_HOUR,
                        "event": "last_gasp" if tripped else None,
                        "is_simulated": True,
                    },
                )


def stdout_publisher() -> Publish:
    def publish(batch: list[tuple[str, dict[str, Any]]]) -> None:
        for clamp_id, payload in batch:
            print(json.dumps({"clamp_id": clamp_id, "payload": payload}), flush=True)

    return publish


def http_publisher(origin: str, device_key: str) -> Publish:
    """POSTs like a real device. The houses of one tick go in parallel: each request opens its own
    database connection on the server, about a second over a slow link."""
    pool = ThreadPoolExecutor(max_workers=len(config.HOMES))

    def post(clamp_id: str, payload: dict[str, Any]) -> None:
        request = urllib.request.Request(  # noqa: S310 - origin from the operator
            f"{origin.rstrip('/')}/api/v1/devices/{clamp_id}/readings",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "X-Device-Key": device_key},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_S):  # noqa: S310 - origin from the operator
                pass
        except OSError as error:
            print(f"[sim] {clamp_id}: {error}", file=sys.stderr)

    def publish(batch: list[tuple[str, dict[str, Any]]]) -> None:
        for clamp_id, payload in batch:
            pool.submit(post, clamp_id, payload)

    return publish


def _listen_keys(switches: Switches, stop: threading.Event) -> None:
    keys = {"h": "heat", "e": "ev", "t": "trip"}
    for line in sys.stdin:
        key = line.strip().lower()[:1]
        if key == "q":
            stop.set()
            return
        if key == "r":
            switches.set("trip", False)
        elif key in keys:
            switches.set(keys[key], not getattr(switches, keys[key]))


def _serve_controls(switches: Switches) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - http.server's naming
            for name, values in parse_qs(urlparse(self.path).query).items():
                if name in ("heat", "ev", "trip"):
                    switches.set(name, values[0] == "on")
            body = json.dumps(vars(switches)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            return

    HTTPServer(("127.0.0.1", CONTROL_PORT), Handler).serve_forever()


def run_live(publish: Publish, scripted: bool, keys: bool) -> None:
    rig, stop = Rig(), threading.Event()
    threading.Thread(target=_serve_controls, args=(rig.switches,), daemon=True).start()
    if keys:
        threading.Thread(target=_listen_keys, args=(rig.switches, stop), daemon=True).start()
    start, pending = time.monotonic(), list(SCRIPT) if scripted else []
    while not stop.is_set():
        elapsed = time.monotonic() - start
        while pending and pending[0][0] <= elapsed:
            _, name, on = pending.pop(0)
            rig.switches.set(name, on)
        publish(list(rig.step(datetime.now(UTC))))
        stop.wait(config.SAMPLE_INTERVAL_S)


def run_replay(publish: Publish, capture: Path, speed: float) -> None:
    """Replays a capture (from `silip.bench.record`) with its original timing.

    Timestamps move to now, and every row is labeled simulated: a replay is not live data.
    """
    lines = [json.loads(line) for line in capture.read_text(encoding="utf-8").splitlines() if line]
    start = time.monotonic()
    for line in lines:
        delay = line["t"] / speed - (time.monotonic() - start)
        if delay > 0:
            time.sleep(delay)
        payload = {**line["payload"], "ts": datetime.now(UTC).isoformat(), "is_simulated": True}
        publish([(line["clamp_id"], payload)])


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="SILIP bench simulator (is_simulated=true)")
    out = parser.add_mutually_exclusive_group(required=True)
    out.add_argument(
        "--http", metavar="ORIGIN", help="POST to this API like a device (needs BENCH_DEVICE_KEY)"
    )
    out.add_argument(
        "--stdout", action="store_true", help="print JSON lines for silip.ingest.local"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--script", action="store_true", help="run the 2-minute story")
    mode.add_argument("--replay", type=Path, metavar="FILE", help="replay a recorded capture")
    parser.add_argument("--speed", type=float, default=config.REPLAY_SPEED)
    args = parser.parse_args(argv)

    if args.http:
        key = os.environ.get("BENCH_DEVICE_KEY")
        if not key:
            parser.error("set BENCH_DEVICE_KEY to the bench devices' key")
        publish = http_publisher(args.http, key)
    else:
        publish = stdout_publisher()
    if args.replay:
        run_replay(publish, args.replay, args.speed)
    else:
        # Typed keys only when stdout is not a pipe into ingest (the terminal is free for them).
        run_live(publish, scripted=args.script, keys=not args.stdout and not args.script)


if __name__ == "__main__":
    main()

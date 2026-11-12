# Live demo runbook (Priority 1: steps 0 to 3)

The 2-minute "mini barangay on the table". Everything here works with no hardware: the bench simulator plays the rig, and the same simulator is the fallback. Rig values (watts, ratings, thresholds) live in one place: `api/src/silip/shared/bench/config.py`.

Steps 4 (city what-if) and 5 (trip and outage) are not built yet.

## Setup (the day before)
1. `uv sync`, then seed the rig's records once: `uv run python -m silip.bench.seed` (inserts only; safe to rerun).
2. Record a clean run for Replay: run the story once (below), then `uv run python -m silip.bench.record --minutes 3 --out demo/capture.jsonl`. Keep two copies.
3. Make a QR code point at `https://<web-origin>/demo`. The page also draws its own QR in the top right on wide screens.
4. Phone hotspot as a backup network. Venue Wi-Fi to Neon was slow in rehearsal (see Risks).

## Start (laptop, 1 minute before)
Local rehearsal, no deploy needed:
```bash
make api                     # terminal 1: API on :8000
make web                     # terminal 2: web on :5173, open http://localhost:5173/demo
uv run python -m silip.bench.sim --stdout | uv run python -m silip.ingest.local   # terminal 3
```
Against the deployed API, once the HTTPS device ingest from `feature/iot` is on `dev`:
```bash
BENCH_DEVICE_KEY=<bench key> uv run python -m silip.bench.sim --http https://<api-origin>
```

Switches (any of these):
- In the browser or with curl: `http://127.0.0.1:8765/?heat=on`, `?ev=on`, `?heat=off&ev=off`.
- In the simulator's terminal (when not piped): `h` heat, `e` EV, `q` quit, then Enter.
- Hands-free: start with `--script` and it runs the timeline below by itself.

## The 2 minutes
| Time | Do | Screen shows | Say |
|---|---|---|---|
| 0:00 | Show the QR. | `/demo` opens on phones, no sign-in. "Replay (simulated)" or "Live rig" under the title. | "Scan this. It is the same page on your phone." |
| 0:10 | Point at Transformer T1. | Each home's watts and volts. T1's total, "built from 4 of 4 homes by SIN", about 55% of rating, OK. | "Every home has a clamp. We add them up by Service ID to get the transformer." |
| 0:20 | Heat wave on. | T1 climbs to about 95%. Watch (amber) within about 6 s. | "A hot night. Every aircon turns on." |
| 0:40 | EV on. | T1 passes 100%. Critical within about 6 to 10 s. Reasons: "Load 130% of rating now", "House 3 added a large new load (likely EV)". | "One neighbour plugs in an EV. Now T1 is over its rating, and SILIP says why." |
| 1:00 | Point at the top card. | "House 4: records say T1, voltage says T2 (confidence over 99%)". House 4's voltage matches T2's, not T1's. | "The records put House 4 on T1. Its voltage moves with T2. The records are wrong, and now we know." |
| 1:20 | EV off, heat off. | T1 back to Watch, then OK. | "When the load drops, so does the risk." |

The `--script` timeline: heat at 20 s, EV at 40 s, then the trip at 95 s and restore at 115 s (step 5 is not built yet, so skip those beats), and everything off at 125 s.

## Switch to Replay in under 5 seconds
If the rig or the network fails mid-demo:
1. Stop the live feed: Ctrl+C in terminal 3.
2. Press Up, edit to the replay command, Enter. Better: keep this line ready in a 4th terminal:
   `uv run python -m silip.bench.sim --stdout --replay demo/capture.jsonl | uv run python -m silip.ingest.local`
3. The page picks it up on its next 2 s poll. The label reads "Replay (simulated)".

## Rehearse (5 runs before the demo)
- [ ] 3 runs with `--script`, timing steps 2 and 3 against the table above.
- [ ] 1 run where you switch to Replay mid-story, in under 5 s.
- [ ] 1 run with the rig unplugged (or the simulator stopped): the page shows "Waiting for the rig" and keeps the last good numbers visible.
- [ ] Check `/demo` on a phone at the venue, on the venue network and on the hotspot.

## Measured in the dry run (simulator, laptop to Neon)
- Heat on to Watch on screen: 5.4 s and 7.3 s (two runs).
- EV on to Critical on screen: 6.7 s, 5.9 s and 9.8 s (three runs). The EV reason appears together with Critical.
- Most of that is deliberate: the rule needs 3 samples in a row (6 s) before it changes tier. This stands in for the real rule's 2 hours (`HOLD_SAMPLES`).
- House 4 flag: shows about 25 s after the heat wave starts, once enough load change is in the 2-minute window.

## Risks
- **Network to Neon.** From the laptop, API reads took 0.7 s typically but stalled for 4 to 50 s at times, while the database itself answered in under 1 ms. Deployed (API and Neon in the cloud) this should be much faster. Rehearse on the venue network, and keep Replay ready.
- **Rig values are starting points.** Match `config.py` to the built rig: ratings, voltage and series resistance. See `docs/demo/hardware.md` (in progress).

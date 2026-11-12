# Firmware rules (`iot/`)

On top of [engineering-standards.md](engineering-standards.md). Hardware facts live in `docs/SPEC.md#hardware`.

- The node **measures only**. It never switches, diverts or interrupts power. Nothing touches Meralco's meter, seal, service drop or transformer.
- A licensed electrician installs the clamp on the customer side, after the meter. Bench demos stay at 12 V.
- PlatformIO. Code split by job:
  - `lib/sensor/`: ADC reads
  - `lib/power/`: RMS, kW, PF. Pure math, no Arduino headers, so it runs in native tests.
  - `lib/transport/`: `Transport` interface; `MqttTransport` now, LoRa later
  - `include/config.h`: pins, calibration, intervals
- Secrets in `include/secrets.h` (git-ignored). Commit only `secrets.example.h`.
- The payload matches `schemas/reading.json` (exported from `silip_ml.readings.domain`) exactly. Topic: `silip/v1/{transformer_id}/{sin_hash}/reading`. The device stores only `sin_hash`, never the raw SIN.
- `lib/power/` has native unit tests: `pio test -e native`.

# iot

ESP32 + SCT-013-000 clamp node (PlatformIO). It measures household current and voltage after the meter and publishes one reading per interval over MQTT. It never switches power.

- `lib/sensor` reads the ADC, `lib/power` computes RMS, kW and PF (pure math), `lib/transport` sends (`MqttTransport` now, LoRa later behind the same `Transport` interface).
- Copy `include/secrets.example.h` to `include/secrets.h` (git-ignored) and fill Wi-Fi, broker and the household's `sin_hash`.
- Build `pio run -e esp32dev`; test the math on your computer with `pio test -e native`. Payload: `schemas/reading.json`.

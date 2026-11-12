# iot

ESP32 + SCT-013-000 clamp node (PlatformIO). It measures household current and voltage after the meter and sends one HTTP(S) report per interval to the API/Lambda. It never switches power.

- Register the device in the dashboard, enter its Wi-Fi details, and download `secrets.h` into `include/` (git-ignored). See [device registration](../docs/iot-management.md).
- `lib/sensor` reads the ADC, `lib/power` computes RMS, kW and PF, and `lib/transport/HttpTransport` sends readings using the generated device key.
- Build `pio run -e esp32dev`; test the math with `pio test -e native`. Sender schema: `schemas/device-reading.json`.
- Deployed nodes use HTTPS. The included public Amazon Root CA 1 validates the default CloudFront domain. A custom server with a different certificate issuer needs its corresponding trusted CA; never disable certificate verification.

# IoT Reading Payload Specification

This document explains the example message in [`payload.example.json`](payload.example.json), the project requirements each field serves, and the boundary between the implemented reading contract and proposed MPU6050 telemetry.

## Purpose and data flow

The ESP32 clamp node reports household electrical measurements so SILIP can resample readings into 15-minute intervals, aggregate opted-in household load by transformer, and support transformer risk estimates. The node measures only; it does not switch, divert, or interrupt power.

The intended path is ESP32 → MQTT over TLS → AWS IoT Core topic rule → ingestion Lambda → database → API → website. The website does not receive the device message directly. The current MQTT topic format is:

```text
silip/v1/{transformer_id}/{sin_hash}/reading
```

## Field reference

| Field | Type / unit | Meaning and objective | Contract status |
|---|---|---|---|
| `sin_hash` | string, 64 lowercase hex characters | Salted SHA-256 household identifier used to associate opted-in readings without transmitting the raw SIN. Required for household/transformer aggregation. | Supported; never put the raw SIN in the payload. The all-zero example is a placeholder and must not identify a real household. |
| `transformer_id` | string, 1–32 characters | Identifier of the serving transformer. Used to group readings for transformer load and risk estimates. | Supported; `T-104` is illustrative and must be replaced with the assigned ID. |
| `ts` | ISO 8601 timestamp with timezone | Time associated with the reading. Enables correct ordering and 15-minute resampling. | Supported; example uses Philippine time (`+08:00`). Device time must be synchronized and timezone-aware. |
| `voltage_v` | number, volts RMS | AC voltage measured from the voltage-reference input. Used with current to estimate apparent and real power. | Supported by the existing design; the SCT-013-000 itself measures current, not voltage. Range in the schema is 0–300 V. |
| `current_a` | number, amperes RMS | Household line current measured using the SCT-013-000 clamp and signal-conditioning/ADC circuit. | Supported; schema range is 0–100 A. Calibration must be verified per node against a reference meter. |
| `power_kw` | number, kilowatts | Estimated real power. Used by SILIP's load aggregation and transformer risk calculations. Can be negative for export if the measurement method supports direction. | Supported; no numeric bounds in the current schema. Sign/export behavior must be validated for the chosen voltage/current sensing hardware. |
| `power_factor` | number, unitless, 0–1 | Ratio of real power to apparent power for the measured AC signals. Helps convert voltage × current into a real-power estimate. | Supported; computed from sampled waveforms, not read from a separate sensor. Current calculation and calibration need hardware validation. |
| `energy_kwh_interval` | number, kilowatt-hours | Estimated energy over the reporting interval. Supports interval usage and consistency checks against power over time. | Supported; firmware currently publishes every 15 minutes. The example `0.61 kWh` is approximately `2.43 kW × 0.25 h`. |
| `event` | `null` or `"last_gasp"` | Optional event marker for a final report when the node detects impending power loss. | Supported by the schema. `null` means no event. |
| `is_simulated` | boolean | Identifies sample or generated data so it cannot be mistaken for a real measurement. | Optional in the schema, but include it in fixtures; this example is `true`. Real device reports should be `false`. |
| `motion` | object (proposal) | Proposed MPU6050 accelerometer/gyroscope telemetry for detecting device movement or disturbance. | **Not supported by the current schema, firmware, ingestion/storage path, or website API.** The example includes this proposed object and therefore is not accepted by the current strict ingestion validator. |

## Motion object proposal

The example's proposed `motion` object contains:

| Field | Type / unit | Intended interpretation | Important limitation |
|---|---|---|---|
| `sensor` | string | Sensor model identifier (`MPU6050`). | Identifies the source; does not prove the sensor is connected or calibrated. |
| `accel_m_s2.x/y/z` | numbers, m/s² | Acceleration along the sensor's three axes. Can reveal shocks, tilt, or movement. | A stationary sensor measures gravity. Axes depend on installation orientation; calibrate mounting and filter vibration. |
| `gyro_dps.x/y/z` | numbers, degrees per second | Angular rotation rate around each sensor axis. Can reveal twisting or vibration. | Bias and noise require calibration; sample rate and filtering affect detection. |
| `state` | proposed enum: `stable` or `wiggling` | Firmware classification from a defined motion window and thresholds. | Thresholds, duration, debounce, and false-alarm behavior have not yet been defined or tested. |
| `tamper_assessment` | proposed enum: `normal` or `suspected_tampering` | Indicates movement that warrants inspection. | It is an alert hypothesis, not proof of theft. Handling, vibration, maintenance, or loose mounting can trigger it. Do not label a device `stolen` based on MPU6050 motion alone. |

All motion numbers in `payload.example.json` are illustrative and `is_simulated` is true. The MPU6050 does not provide a reliable measurement of enclosure or ambient temperature. No temperature field is currently defined; add a specified temperature sensor and its units/placement before reporting temperature as a project measurement.

## Power factor, plainly

Apparent power is approximately RMS voltage multiplied by RMS current and is measured in volt-amperes (VA). Real power is the portion transferred to appliances, in watts (W). Power factor is real power divided by apparent power, so:

```text
real_power_W ≈ voltage_RMS_V × current_RMS_A × power_factor
```

For the illustrative values, `219.8 V × 11.6 A ≈ 2,550 VA`; multiplying by `0.95` gives about `2,423 W`, or `2.42 kW`. The example's `2.43 kW` is consistent within rounding. This is an AC waveform estimate; firmware must sample voltage and current with appropriate timing to estimate real power and power factor correctly.

## Contract and integration requirements

- The source of truth is `silip/ml/src/silip_ml/readings/domain.py`; `silip/schemas/reading.json` is generated from that model. The model currently forbids extra fields.
- Current firmware in `iot/src/main.cpp` emits only the electrical fields and `event`; it does not read an MPU6050 or temperature sensor.
- The ingestion Lambda validates with the same strict `Reading` model. Unknown fields such as `motion` cause the current message to be rejected. The current database insert also has no motion columns, and the website API does not expose motion.
- Before sending `motion` from a real node, define and implement it in the Pydantic model, regenerate the JSON Schema, design persistence/migration and ingestion behavior, then expose the needed data through the API/UI. Add calibrated firmware acquisition and explicit motion thresholds, units, sampling window, and false-alarm handling.
- Keep raw SINs, Wi-Fi credentials, broker credentials, and certificates out of payloads and committed files. The node uses only the salted `sin_hash` for household association.
- Treat movement as a tamper signal requiring review. It does not establish theft or identify who moved the device.

## Example status

`payload.example.json` is a simulated design example that combines the existing electrical payload with the proposed motion object. Because `motion` is not part of the current v1 schema, the complete example is **not a valid current production ingestion message**. Use the electrical fields alone when exercising the current firmware/backend contract.

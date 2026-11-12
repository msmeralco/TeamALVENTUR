#pragma once
// Pins, calibration and timing. Hardware: docs/SPEC.md#hardware.

// ADS1115 channels: A0 = SCT-013-000 across the 22 ohm burden, A1 = 9 V AC-AC voltage reference.
constexpr int ADC_CURRENT_CHANNEL = 0;
constexpr int ADC_VOLTAGE_CHANNEL = 1;

// Calibration factors, set per node on the bench against a reference meter. [VERIFY] per unit.
constexpr float CURRENT_AMPS_PER_VOLT = 100.0f / (0.05f * 22.0f);  // 100 A : 50 mA CT into 22 ohm
constexpr float VOLTAGE_VOLTS_PER_VOLT = 1.0f;                      // set from the AC-AC divider

constexpr int SAMPLES_PER_READING = 400;
constexpr unsigned long PUBLISH_INTERVAL_MS = 15UL * 60UL * 1000UL;  // matches the 15-min resample

// Payload topic: silip/v1/{transformer_id}/{sin_hash}/reading (see schemas/reading.json).
constexpr const char* TOPIC_FORMAT = "silip/v1/%s/%s/reading";

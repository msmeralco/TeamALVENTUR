#pragma once
// Pure power math on sampled waveforms. No Arduino headers, so it runs in native tests.

#include <cstddef>

struct PowerReading {
  float voltage_v;
  float current_a;
  float power_kw;
  float power_factor;
};

// Root mean square of `n` samples. Returns 0 for n == 0.
float rms(const float* samples, std::size_t n);

// Real power, RMS values and power factor from simultaneous voltage (V) and current (A) samples.
PowerReading compute_power(const float* volts, const float* amps, std::size_t n);

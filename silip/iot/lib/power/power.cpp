#include "power.h"

#include <cmath>

float rms(const float* samples, std::size_t n) {
  if (n == 0) return 0.0f;
  double sum = 0.0;
  for (std::size_t i = 0; i < n; ++i) sum += static_cast<double>(samples[i]) * samples[i];
  return static_cast<float>(std::sqrt(sum / n));
}

PowerReading compute_power(const float* volts, const float* amps, std::size_t n) {
  PowerReading reading{rms(volts, n), rms(amps, n), 0.0f, 0.0f};
  if (n == 0) return reading;
  double real_w = 0.0;
  for (std::size_t i = 0; i < n; ++i) real_w += static_cast<double>(volts[i]) * amps[i];
  real_w /= n;
  const double apparent_va = static_cast<double>(reading.voltage_v) * reading.current_a;
  reading.power_kw = static_cast<float>(real_w / 1000.0);
  reading.power_factor = apparent_va > 0.0 ? static_cast<float>(std::fabs(real_w) / apparent_va) : 0.0f;
  return reading;
}

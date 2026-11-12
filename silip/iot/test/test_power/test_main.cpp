// Native tests for lib/power: pio test -e native
#include <unity.h>

#include <cmath>

#include "power.h"

namespace {
constexpr std::size_t N = 1000;
constexpr float PI_F = 3.14159265f;
float volts[N];
float amps[N];

void sine(float* out, float peak, float phase) {
  for (std::size_t i = 0; i < N; ++i) out[i] = peak * std::sin(2 * PI_F * 10 * i / N + phase);
}
}  // namespace

void setUp() {}
void tearDown() {}

void test_rms_of_sine_is_peak_over_root_two() {
  sine(volts, 325.0f, 0.0f);
  TEST_ASSERT_FLOAT_WITHIN(0.5f, 325.0f / std::sqrt(2.0f), rms(volts, N));
}

void test_in_phase_load_has_unity_power_factor() {
  sine(volts, 325.0f, 0.0f);
  sine(amps, 14.1f, 0.0f);
  const PowerReading r = compute_power(volts, amps, N);
  TEST_ASSERT_FLOAT_WITHIN(0.01f, 1.0f, r.power_factor);
  TEST_ASSERT_FLOAT_WITHIN(0.02f, 325.0f * 14.1f / 2 / 1000, r.power_kw);
}

void test_lagging_load_lowers_power_factor() {
  sine(volts, 325.0f, 0.0f);
  sine(amps, 14.1f, -PI_F / 3);  // 60 degrees: PF = 0.5
  TEST_ASSERT_FLOAT_WITHIN(0.01f, 0.5f, compute_power(volts, amps, N).power_factor);
}

void test_no_samples_is_zero() {
  TEST_ASSERT_EQUAL_FLOAT(0.0f, rms(volts, 0));
}

int main() {
  UNITY_BEGIN();
  RUN_TEST(test_rms_of_sine_is_peak_over_root_two);
  RUN_TEST(test_in_phase_load_has_unity_power_factor);
  RUN_TEST(test_lagging_load_lowers_power_factor);
  RUN_TEST(test_no_samples_is_zero);
  return UNITY_END();
}

#include "sensor.h"

#include <Adafruit_ADS1X15.h>

#include "config.h"

namespace {
Adafruit_ADS1115 ads;

void remove_offset(float* samples, std::size_t n) {
  double mean = 0.0;
  for (std::size_t i = 0; i < n; ++i) mean += samples[i];
  mean /= n;
  for (std::size_t i = 0; i < n; ++i) samples[i] -= static_cast<float>(mean);
}
}  // namespace

bool sensor_begin() {
  if (!ads.begin()) return false;
  ads.setGain(GAIN_ONE);
  ads.setDataRate(RATE_ADS1115_860SPS);
  return true;
}

void sensor_sample(float* volts, float* amps, std::size_t n) {
  for (std::size_t i = 0; i < n; ++i) {
    volts[i] = ads.computeVolts(ads.readADC_SingleEnded(ADC_VOLTAGE_CHANNEL)) * VOLTAGE_VOLTS_PER_VOLT;
    amps[i] = ads.computeVolts(ads.readADC_SingleEnded(ADC_CURRENT_CHANNEL)) * CURRENT_AMPS_PER_VOLT;
  }
  remove_offset(volts, n);  // the bias network centers both signals at mid-supply
  remove_offset(amps, n);
}

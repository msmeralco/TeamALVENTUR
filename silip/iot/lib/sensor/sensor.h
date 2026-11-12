#pragma once
// Reads simultaneous voltage and current samples from the ADS1115.

#include <cstddef>

// Starts the ADC. Returns false if the ADS1115 does not answer on I2C.
bool sensor_begin();

// Fills `volts` and `amps` with `n` calibrated samples (V and A, DC offset removed).
void sensor_sample(float* volts, float* amps, std::size_t n);

// SILIP clamp node: sample, compute, publish. Measures only; never switches power.
#include <Arduino.h>
#include <time.h>

#include "config.h"
#include "mqtt_transport.h"
#include "power.h"
#include "secrets.h"
#include "sensor.h"

namespace {
float volts[SAMPLES_PER_READING];
float amps[SAMPLES_PER_READING];
MqttTransport transport;  // swap for a LoRa transport here; nothing else changes
unsigned long last_publish_ms = 0;

void iso_timestamp(char* out, size_t size) {
  time_t now = time(nullptr);
  struct tm local;
  localtime_r(&now, &local);
  strftime(out, size, "%Y-%m-%dT%H:%M:%S+08:00", &local);
}
}  // namespace

void setup() {
  Serial.begin(115200);
  configTime(8 * 3600, 0, "pool.ntp.org");  // Asia/Manila, UTC+8
  if (!sensor_begin()) Serial.println("ADS1115 not found");
  transport.connect();
}

void loop() {
  transport.loop();
  if (millis() - last_publish_ms < PUBLISH_INTERVAL_MS && last_publish_ms != 0) return;
  const unsigned long elapsed_ms = last_publish_ms == 0 ? PUBLISH_INTERVAL_MS : millis() - last_publish_ms;
  last_publish_ms = millis();

  sensor_sample(volts, amps, SAMPLES_PER_READING);
  const PowerReading reading = compute_power(volts, amps, SAMPLES_PER_READING);
  const float energy_kwh = reading.power_kw * (elapsed_ms / 3600000.0f);

  char ts[32];
  iso_timestamp(ts, sizeof ts);
  char topic[128];
  snprintf(topic, sizeof topic, TOPIC_FORMAT, TRANSFORMER_ID, SIN_HASH);
  char json[384];
  snprintf(json, sizeof json,
           "{\"sin_hash\":\"%s\",\"transformer_id\":\"%s\",\"ts\":\"%s\",\"voltage_v\":%.1f,"
           "\"current_a\":%.2f,\"power_kw\":%.3f,\"power_factor\":%.2f,\"energy_kwh_interval\":%.3f,"
           "\"event\":null}",
           SIN_HASH, TRANSFORMER_ID, ts, reading.voltage_v, reading.current_a, reading.power_kw,
           reading.power_factor, energy_kwh);
  if (!transport.publish(topic, json)) Serial.println("publish failed; will retry next interval");
}

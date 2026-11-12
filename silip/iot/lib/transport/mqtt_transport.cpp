#include "mqtt_transport.h"

#include <WiFi.h>

#include "secrets.h"

namespace {
constexpr unsigned long WIFI_TIMEOUT_MS = 20000;
constexpr int MAX_PAYLOAD_BYTES = 512;
}  // namespace

MqttTransport::MqttTransport() : client_(tls_) {
  tls_.setCACert(ROOT_CA_PEM);
  tls_.setCertificate(DEVICE_CERT_PEM);
  tls_.setPrivateKey(DEVICE_KEY_PEM);
  client_.setServer(MQTT_HOST, MQTT_PORT);
  client_.setBufferSize(MAX_PAYLOAD_BYTES);
}

bool MqttTransport::connect() {
  if (WiFi.status() != WL_CONNECTED) {
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    const unsigned long start = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - start < WIFI_TIMEOUT_MS) delay(250);
    if (WiFi.status() != WL_CONNECTED) return false;
  }
  return client_.connected() || client_.connect(MQTT_CLIENT_ID);
}

bool MqttTransport::publish(const char* topic, const char* json) {
  return connect() && client_.publish(topic, json);
}

void MqttTransport::loop() { client_.loop(); }

#pragma once

#include <PubSubClient.h>
#include <WiFiClientSecure.h>

#include "transport.h"

// MQTT over TLS to AWS IoT Core (mutual TLS with the thing certificate).
class MqttTransport : public Transport {
 public:
  MqttTransport();
  bool connect() override;
  bool publish(const char* topic, const char* json) override;
  void loop() override;

 private:
  WiFiClientSecure tls_;
  PubSubClient client_;
};

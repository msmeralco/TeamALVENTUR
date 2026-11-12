#pragma once
#include <WiFiClientSecure.h>
#include <WiFi.h>
#include "transport.h"

// Direct HTTPS to the SILIP API/Lambda using a dashboard-issued device key.
class HttpTransport : public Transport {
 public:
  HttpTransport();
  bool connect() override;
  bool publish(const char* endpoint, const char* json) override;
  void loop() override {}
 private:
  WiFiClientSecure tls_;
  WiFiClient plain_;
};

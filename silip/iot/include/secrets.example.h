#pragma once
// Copy to secrets.h (git-ignored) and fill in. Never commit secrets.h.
// The device stores only the salted sin_hash, never the raw SIN.

constexpr const char* WIFI_SSID = "your-wifi";
constexpr const char* WIFI_PASSWORD = "change-me";

constexpr const char* MQTT_HOST = "your-iot-endpoint.iot.ap-southeast-1.amazonaws.com";
constexpr int MQTT_PORT = 8883;
constexpr const char* MQTT_CLIENT_ID = "silip-node-0001";

constexpr const char* TRANSFORMER_ID = "T-104";
constexpr const char* SIN_HASH = "0000000000000000000000000000000000000000000000000000000000000000";

// AWS IoT Core uses mutual TLS: paste the PEM strings from the thing certificate.
constexpr const char* ROOT_CA_PEM = "";
constexpr const char* DEVICE_CERT_PEM = "";
constexpr const char* DEVICE_KEY_PEM = "";

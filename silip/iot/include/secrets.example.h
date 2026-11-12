#pragma once
// Download secrets.h from Devices in the dashboard, then build and flash the node.
// Never commit secrets.h or the downloaded setup file.
constexpr const char* WIFI_SSID = "your-wifi";
constexpr const char* WIFI_PASSWORD = "change-me";
constexpr const char* DEVICE_API_URL = "https://your-silip-domain/api/v1/devices/your-device-id/readings";
constexpr const char* DEVICE_KEY = "generated-by-the-dashboard";

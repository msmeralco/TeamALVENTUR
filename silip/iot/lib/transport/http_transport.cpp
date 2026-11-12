#include "http_transport.h"
#include <HTTPClient.h>
#include <cstring>
#include <mbedtls/md.h>
#include "amazon_root_ca.h"
#include "secrets.h"

namespace {
constexpr unsigned long WIFI_TIMEOUT_MS = 20000;
constexpr int CONNECT_TIMEOUT_MS = 5000;
constexpr int REQUEST_TIMEOUT_MS = 10000;
}

HttpTransport::HttpTransport() { tls_.setCACert(AMAZON_ROOT_CA1); }

bool HttpTransport::connect() {
  if (WiFi.status() == WL_CONNECTED) return true;
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  const unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < WIFI_TIMEOUT_MS) delay(250);
  return WiFi.status() == WL_CONNECTED;
}

bool HttpTransport::publish(const char* endpoint, const char* json) {
  if (!connect()) return false;
  HTTPClient http;
  http.setConnectTimeout(CONNECT_TIMEOUT_MS);
  http.setTimeout(REQUEST_TIMEOUT_MS);
  // Plain HTTP is for a local development server; deployed devices use HTTPS.
  const bool ready = strncmp(endpoint, "https://", 8) == 0
      ? http.begin(tls_, endpoint) : http.begin(plain_, endpoint);
  if (!ready) return false;
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-Key", DEVICE_KEY);
  // Required for CloudFront to sign POST bodies for a private Lambda function URL.
  unsigned char digest[32];
  if (mbedtls_md(mbedtls_md_info_from_type(MBEDTLS_MD_SHA256),
      reinterpret_cast<const unsigned char*>(json), strlen(json), digest) != 0) {
    http.end();
    return false;
  }
  char body_hash[65];
  for (int i = 0; i < 32; ++i) snprintf(body_hash + i * 2, 3, "%02x", digest[i]);
  body_hash[64] = '\0';
  http.addHeader("x-amz-content-sha256", body_hash);
  const int code = http.POST(String(json));
  http.end();
  return code >= 200 && code < 300;
}

#pragma once
// How a reading leaves the node. HTTPS now; a LoRa transport implements the same interface later.

class Transport {
 public:
  virtual ~Transport() = default;
  // Connects or reconnects. Returns true when ready to publish.
  virtual bool connect() = 0;
  // Sends one JSON payload. Returns false if it was not accepted.
  virtual bool publish(const char* topic, const char* json) = 0;
  // Lets the transport do background work (keep-alive). Call every loop.
  virtual void loop() = 0;
};

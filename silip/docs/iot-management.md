# Register a device

Everything is managed from **Devices** in the dashboard.

Use **Add transformer** to enter a transformer ID, rated capacity, and map coordinates. Estimated homes and metered coverage are optional. The transformer is available for device assignments immediately; the risk map waits for at least seven days of readings before showing a forecast.

1. Click **Register device**. Enter its sticker ID if it has one, or leave the ID blank to generate one.
2. Choose the serving transformer, set the house coordinates, and optionally enter an address or location description. **Use my current location** fills the coordinates when you are at the installation. Coordinates place the house pin on the map; the text label helps people identify it and does not move or geocode the pin. The map also shows the selected serving transformer.
3. Confirm household consent and click **Register device**.
4. Save the setup shown on screen. Enter the device's Wi-Fi details and click **Download device setup** to get `secrets.h`. Wi-Fi details stay in your browser and the downloaded file. Put this file in `iot/include/`, then build and flash the node.

The dashboard generates the household reference and device key automatically. Keep the setup file private. The key is shown once; select **Replace device key** if you lose it. Replacement immediately disables the old key. Existing devices without a key have a **Generate device key** button.

Select a device to see its installation, status, last reading time, and assigned transformer. Change its coordinates, location label, or transformer and click **Save installation**. Future readings use the new transformer automatically; historical readings keep their original assignment.

**Home device totals** adds up 15-minute readings from sensors assigned to the selected transformer. It shows the homes' combined use, not a reading taken from the transformer itself. Missing reports are not counted as zero usage. Simulated readings are labeled. Household users see their own electrical and movement details in **My usage**.

## Sending readings

The node sends JSON directly to the website API, which runs on Lambda in AWS:

```text
POST /api/v1/devices/{device_id}/readings
Content-Type: application/json
X-Device-Key: <key from the dashboard>
```

Use the complete endpoint displayed in the dashboard. The sender contract is generated in `schemas/device-reading.json`; `iot/payload.example.json` is a simulated example. The server resolves the household and transformer from registration, so the node does not need either identifier. Legacy identifiers in a message are ignored in favor of the current registration.

A successful report returns HTTP 204. Invalid or missing keys return 401. Invalid readings return 422. Reports more than five minutes in the future are rejected; synchronize the device clock. Duplicate timestamps for the same household do not add energy twice.

The server stores only a hash of the device key. Registration and key replacement require an engineer account; the reading endpoint always requires the device key, including during local development.

## Local development and deployment

The local replica already has the device-key migration from `db/schema.sql`. See [local database](local-database.md) for startup commands. A node needs an endpoint it can reach: `127.0.0.1` in your laptop browser is not reachable from an ESP32. Use your development server's LAN address for local tests, and HTTPS for deployed devices.

The active Terraform environments use the API Lambda for both dashboard requests and readings. CloudFront forwards POST and PUT requests. The web client and firmware automatically add the body hash required for its private Lambda origin ([AWS reference](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-lambda.html)). Deployment still requires the normal reviewed Terraform plan and database migration; this code change does not deploy cloud resources.

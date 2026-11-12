import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { lazy, Suspense, useState } from "react";
import { Link } from "react-router-dom";
import { api, unwrap, type Schemas } from "../../shared/api/client";
import { PageHead, SimulatedLabel } from "../../shared/ui";
import { Button } from "../../shared/ui/components/button";
import { Card } from "../../shared/ui/components/card";
import { useDocumentTitle } from "../../shared/ui/feedback";

const inputClass = "w-full rounded-md border bg-background p-2 text-sm";
const InstallationMap = lazy(() => import("./InstallationMap").then((module) => ({ default: module.InstallationMap })));

export function DevicesPage() {
  useDocumentTitle("Devices");
  const cache = useQueryClient();
  const [selected, setSelected] = useState<Schemas["Device"] | null>(null);
  const [transformer, setTransformer] = useState("");
  const [installationTransformer, setInstallationTransformer] = useState("");
  const [showAddTransformer, setShowAddTransformer] = useState(false);
  const [houseLat, setHouseLat] = useState<number | null>(null);
  const [houseLon, setHouseLon] = useState<number | null>(null);
  const [locationLabel, setLocationLabel] = useState("");
  const [locationError, setLocationError] = useState("");
  const [setup, setSetup] = useState<{ id: string; key: string } | null>(null);
  const [showKey, setShowKey] = useState(false);
  const [wifiName, setWifiName] = useState("");
  const [wifiPassword, setWifiPassword] = useState("");
  const [serverAddress, setServerAddress] = useState(window.location.origin);
  let endpoint = "";
  let reachableAddress = false;
  try {
    const server = new URL(serverAddress);
    if (["https:", "http:"].includes(server.protocol) && !server.username && !server.password) {
      endpoint = setup ? `${server.origin}/api/v1/devices/${encodeURIComponent(setup.id)}/readings` : "";
      reachableAddress = !(
        ["localhost", "[::1]", "0.0.0.0"].includes(server.hostname) ||
        server.hostname.endsWith(".localhost") ||
        server.hostname.startsWith("127.")
      );
    }
  } catch {
    /* Keep download disabled until the server address is valid. */
  }
  const issueKey = useMutation({
    mutationFn: async (id: string) =>
      unwrap(await api.POST("/api/v1/devices/{clamp_id}/key", { params: { path: { clamp_id: id } } })),
    onSuccess: (data, id) => {
      setSetup({ id, key: data.device_key });
      setShowKey(false);
      void cache.invalidateQueries({ queryKey: ["devices"] });
    },
  });
  function downloadSetup() {
    if (!setup || !endpoint || !reachableAddress) return;
    const header = `#pragma once
// Private device setup. Save as iot/include/secrets.h. Never commit this file.
constexpr const char* WIFI_SSID = ${JSON.stringify(wifiName)};
constexpr const char* WIFI_PASSWORD = ${JSON.stringify(wifiPassword)};
constexpr const char* DEVICE_API_URL = ${JSON.stringify(endpoint)};
constexpr const char* DEVICE_KEY = ${JSON.stringify(setup.key)};
`;
    const file = new Blob([header], { type: "text/plain" });
    const url = URL.createObjectURL(file);
    const link = document.createElement("a");
    link.href = url;
    link.download = "secrets.h";
    link.click();
    URL.revokeObjectURL(url);
  }
  const devices = useQuery({
    queryKey: ["devices"],
    queryFn: async () => unwrap(await api.GET("/api/v1/devices")),
    refetchInterval: 15_000,
  });
  const transformers = useQuery({
    queryKey: ["device-transformers"],
    queryFn: async () => unwrap(await api.GET("/api/v1/devices/transformers")),
  });
  const totals = useQuery({
    queryKey: ["device-totals", transformer],
    queryFn: async () =>
      unwrap(
        await api.GET("/api/v1/devices/transformers/{transformer_id}/telemetry", {
          params: { path: { transformer_id: transformer } },
        }),
      ),
    enabled: !!transformer,
    refetchInterval: 15_000,
  });
  const addTransformer = useMutation({
    mutationFn: async (form: HTMLFormElement) => {
      const values = new FormData(form);
      const result = await api.POST("/api/v1/devices/transformers", {
        body: {
          transformer_id: String(values.get("transformer_id") ?? "").trim(),
          rated_kva: Number(values.get("rated_kva")),
          lat: Number(values.get("lat")),
          lon: Number(values.get("lon")),
          homes: Number(values.get("homes") ?? 0),
          coverage_pct: Number(values.get("coverage_percent") ?? 0) / 100,
          is_simulated: values.get("simulated") === "on",
        },
      });
      if (!result.response.ok) {
        const error = result.error;
        throw new Error(
          error && "detail" in error && typeof error.detail === "string"
            ? error.detail
            : "Could not add transformer. Check the fields and try again.",
        );
      }
      return unwrap(result);
    },
    onSuccess: (created) => {
      setInstallationTransformer(created.transformer_id);
      setTransformer(created.transformer_id);
      setShowAddTransformer(false);
      void cache.invalidateQueries({ queryKey: ["device-transformers"] });
      void cache.invalidateQueries({ queryKey: ["transformers"] });
    },
  });
  const save = useMutation({
    mutationFn: async (form: HTMLFormElement) => {
      const values = new FormData(form);
      const installation = {
        transformer_id: String(values.get("transformer_id")),
        lat: Number(values.get("lat")),
        lon: Number(values.get("lon")),
        location_label: String(values.get("location_label") ?? "").trim() || null,
      };
      const result = selected
        ? await api.PUT("/api/v1/devices/{clamp_id}/installation", {
            params: { path: { clamp_id: selected.clamp_id } },
            body: installation,
          })
        : await api.POST("/api/v1/devices", {
            body: {
              ...installation,
              clamp_id: String(values.get("clamp_id") ?? "").trim() || undefined,
              ct_model: String(values.get("ct_model")),
              consent_confirmed: values.get("consent") === "on",
              is_simulated: values.get("simulated") === "on",
            },
          });
      if (!result.response.ok) {
        const error = result.error;
        throw new Error(
          error && "detail" in error && typeof error.detail === "string"
            ? error.detail
            : "Could not save. Check the fields and try again.",
        );
      }
      return unwrap(result);
    },
    onSuccess: (device) => {
      setSelected(device);
      if ("device_key" in device && typeof device.device_key === "string") {
        setSetup({ id: device.clamp_id, key: device.device_key });
        setShowKey(false);
      }
      setTransformer(device.transformer_id);
      setInstallationTransformer(device.transformer_id);
      setHouseLat(device.lat);
      setHouseLon(device.lon);
      setLocationLabel(device.location_label ?? "");
      void cache.invalidateQueries({ queryKey: ["devices"] });
      void cache.invalidateQueries({ queryKey: ["device-totals"] });
      void cache.invalidateQueries({ queryKey: ["clamps"] });
    },
  });
  const current = devices.data?.find((d) => d.clamp_id === selected?.clamp_id) ?? selected;
  function locate(form: HTMLFormElement) {
    setLocationError("");
    if (!navigator.geolocation) {
      setLocationError("Location is unavailable. Enter coordinates manually.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        (form.elements.namedItem("lat") as HTMLInputElement).value = String(position.coords.latitude);
        (form.elements.namedItem("lon") as HTMLInputElement).value = String(position.coords.longitude);
        setHouseLat(position.coords.latitude);
        setHouseLon(position.coords.longitude);
      },
      () => setLocationError("Location was unavailable. Enter the installation coordinates manually."),
      { timeout: 10_000, enableHighAccuracy: true },
    );
  }
  return (
    <section>
      <PageHead
        title="Devices"
        lede="Register home clamps, locate installations, and choose which transformer serves each home."
      />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="flex min-h-0 flex-col self-start p-6 shadow-none">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold">Installed devices</h2>
            <div className="flex flex-wrap justify-end gap-2">
              <Button
                variant="outline"
                onClick={() => {
                  setShowAddTransformer(!showAddTransformer);
                  addTransformer.reset();
                }}
              >
                Add transformer
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setSelected(null);
                  setSetup(null);
                  setInstallationTransformer("");
                  setHouseLat(null);
                  setHouseLon(null);
                  setLocationLabel("");
                  issueKey.reset();
                  save.reset();
                }}
              >
                Register device
              </Button>
            </div>
          </div>
          {devices.isPending && <p role="status">Loading devices…</p>}
          {devices.isError && (
            <p role="alert">
              Could not load devices. <button onClick={() => void devices.refetch()}>Try again</button>
            </p>
          )}
          {devices.data?.length === 0 && <p>No devices registered. Add your first household clamp.</p>}
          <ul className="max-h-96 overflow-y-auto">
            {devices.data?.map((d) => (
              <li key={d.clamp_id} className="border-b py-3">
                <button
                  className="w-full text-left"
                  onClick={() => {
                    setSelected(d);
                    setSetup(null);
                    issueKey.reset();
                    setTransformer(d.transformer_id);
                    setInstallationTransformer(d.transformer_id);
                    setHouseLat(d.lat);
                    setHouseLon(d.lon);
                    setLocationLabel(d.location_label ?? "");
                    save.reset();
                  }}
                >
                  <span className="font-semibold">{d.clamp_id}</span>
                  <span className="block text-sm text-muted-foreground">
                    {d.location_label ? `${d.location_label} · ` : ""}
                    {d.transformer_id} · {d.status}
                  </span>
                  <SimulatedLabel show={d.is_simulated} />
                </button>
              </li>
            ))}
          </ul>
        </Card>
        <Card className="p-6 shadow-none">
          <h2 className="text-lg font-semibold">{selected ? selected.clamp_id : "Register a device"}</h2>
          {current && (
            <dl className="text-sm">
              <dt>Sensor</dt>
              <dd>{current.ct_model}</dd>
              <dt>Installed</dt>
              <dd>{new Date(current.installed_at).toLocaleString()}</dd>
              <dt>Last reading</dt>
              <dd>
                {current.last_seen_at ? new Date(current.last_seen_at).toLocaleString() : "Awaiting first reading"}
              </dd>
              <dt>Status</dt>
              <dd>{current.status}</dd>
              <dt>Serving transformer</dt>
              <dd>{current.transformer_id}</dd>
              <dt>House location</dt>
              <dd>{current.location_label || "No address or location description provided"}</dd>
            </dl>
          )}
          <form
            key={selected?.clamp_id ?? "new"}
            className="grid gap-4"
            onSubmit={(e) => {
              e.preventDefault();
              save.mutate(e.currentTarget);
            }}
          >
            {!selected && (
              <>
                <label>
                  Device ID (optional)
                  <input
                    name="clamp_id"
                    placeholder="Generated automatically"
                    pattern="[a-zA-Z0-9:_-]{1,128}"
                    className={inputClass}
                  />
                </label>
                <label>
                  Sensor model
                  <input required name="ct_model" defaultValue="SCT-013-000" maxLength={64} className={inputClass} />
                </label>
              </>
            )}
            <label>
              Serving transformer
              <select
                required
                name="transformer_id"
                value={installationTransformer}
                onChange={(e) => setInstallationTransformer(e.target.value)}
                className={inputClass}
              >
                <option value="" disabled>
                  Select a transformer
                </option>
                {transformers.data?.map((t) => (
                  <option key={t.transformer_id} value={t.transformer_id}>
                    {t.transformer_id}
                    {t.is_simulated ? " (simulated)" : ""}
                  </option>
                ))}
              </select>
            </label>
            <p className="-mt-3 text-xs text-muted-foreground">
              This is the transformer the home sensor is assigned to. The map marks it with a T.
            </p>
            {transformers.isError && (
              <p role="alert">
                Could not load transformers.{" "}
                <button type="button" onClick={() => void transformers.refetch()}>
                  Try again
                </button>
              </p>
            )}
            <div className="grid grid-cols-2 gap-3">
              <label>
                House latitude
                <input
                  required
                  type="number"
                  step="any"
                  min={-90}
                  max={90}
                  name="lat"
                  value={houseLat ?? ""}
                  onChange={(e) => setHouseLat(e.target.value === "" ? null : Number(e.target.value))}
                  className={inputClass}
                />
              </label>
              <label>
                House longitude
                <input
                  required
                  type="number"
                  step="any"
                  min={-180}
                  max={180}
                  name="lon"
                  value={houseLon ?? ""}
                  onChange={(e) => setHouseLon(e.target.value === "" ? null : Number(e.target.value))}
                  className={inputClass}
                />
              </label>
            </div>
            <label>
              House address or location description (optional)
              <input
                name="location_label"
                maxLength={200}
                value={locationLabel}
                onChange={(e) => setLocationLabel(e.target.value)}
                placeholder="e.g. 24 Sampaguita St., near the barangay hall"
                className={inputClass}
              />
            </label>
            <p className="-mt-3 text-xs text-muted-foreground">
              The map uses latitude and longitude for the house pin. This text helps people recognize the location; it
              does not geocode or move the pin.
            </p>
            {installationTransformer && transformers.data ? (
              <Suspense fallback={<p role="status">Loading installation map…</p>}>
                <InstallationMap
                  lat={houseLat}
                  lon={houseLon}
                  locationLabel={locationLabel}
                  transformer={
                    transformers.data.find((item) => item.transformer_id === installationTransformer) ?? null
                  }
                />
              </Suspense>
            ) : null}
            <Button
              type="button"
              variant="outline"
              onClick={(e) => {
                const form = e.currentTarget.closest("form");
                if (form) locate(form);
              }}
            >
              Use my current location
            </Button>
            <p className="text-xs text-muted-foreground">
              Use location while at the installation. Verify the serving transformer in the field.
            </p>
            {locationError && <p role="alert">{locationError}</p>}
            {!selected && (
              <>
                <label className="text-sm">
                  <input type="checkbox" name="consent" required /> Household has opted in to measurement and storage of
                  installation coordinates and address/location description
                </label>
                <label className="text-sm">
                  <input type="checkbox" name="simulated" /> Simulated device
                </label>
              </>
            )}
            {selected && (
              <p className="text-sm text-muted-foreground">
                New readings will use this transformer automatically. Historical readings keep their original
                assignment.
              </p>
            )}
            <Button disabled={save.isPending || !transformers.data?.length}>
              {save.isPending ? "Saving…" : selected ? "Save installation" : "Register device"}
            </Button>
            {save.isError && <p role="alert">{save.error.message}</p>}
            {save.isSuccess && <p role="status">Installation saved.</p>}
          </form>
          {current && !setup && (
            <div className="border-t pt-4">
              <Button
                variant="outline"
                disabled={issueKey.isPending}
                onClick={() => {
                  if (
                    current.device_key_set &&
                    !window.confirm("Replace this device key? Its current key will stop working.")
                  )
                    return;
                  issueKey.mutate(current.clamp_id);
                }}
              >
                {issueKey.isPending
                  ? "Generating…"
                  : current.device_key_set
                    ? "Replace device key"
                    : "Generate device key"}
              </Button>
              {issueKey.isError && <p role="alert">Could not generate a key. Try again.</p>}
            </div>
          )}
          {setup && (
            <div className="grid gap-3 border-t pt-4">
              <h3 className="font-semibold">Device registered</h3>
              <p className="text-sm">Save this setup for the device. The key is shown only here.</p>
              <label>
                Device server address
                <input
                  type="url"
                  value={serverAddress}
                  onChange={(e) => setServerAddress(e.target.value)}
                  className={inputClass}
                />
              </label>
              {!reachableAddress && (
                <p role="status" className="text-sm text-muted-foreground">
                  Enter a server address the device can reach. A device cannot use your browser's localhost address.
                </p>
              )}
              <label>
                Send readings to
                <input readOnly value={endpoint} className={inputClass} />
              </label>
              <label>
                Device key
                <input readOnly type={showKey ? "text" : "password"} value={setup.key} className={inputClass} />
              </label>
              <Button type="button" variant="outline" onClick={() => setShowKey(!showKey)}>
                {showKey ? "Hide key" : "Show key"}
              </Button>
              <label>
                Device Wi-Fi name
                <input
                  value={wifiName}
                  onChange={(e) => setWifiName(e.target.value)}
                  autoComplete="off"
                  className={inputClass}
                />
              </label>
              <label>
                Device Wi-Fi password
                <input
                  type="password"
                  value={wifiPassword}
                  onChange={(e) => setWifiPassword(e.target.value)}
                  autoComplete="new-password"
                  className={inputClass}
                />
              </label>
              <p className="text-sm text-muted-foreground">
                Wi-Fi details stay in your browser and the downloaded file.
              </p>
              <Button type="button" disabled={!endpoint || !reachableAddress} onClick={downloadSetup}>
                Download device setup
              </Button>
              <p className="text-sm text-muted-foreground">
                Use the key as the X-Device-Key header when sending readings. Keep the downloaded file private.
              </p>
            </div>
          )}
        </Card>
      </div>
      {showAddTransformer ? (
        <Card className="mt-6 p-6 shadow-none">
          <h2 className="text-lg font-semibold">Add transformer</h2>
          <p className="text-sm text-muted-foreground">
            Add its ID, rated capacity, and coordinates. It will be available for device assignments right away. The
            risk map needs at least seven days of readings before it can forecast the new transformer.
          </p>
          <form
            className="grid gap-4 sm:grid-cols-2"
            onSubmit={(event) => {
              event.preventDefault();
              addTransformer.mutate(event.currentTarget);
            }}
          >
            <label>
              Transformer ID
              <input
                required
                name="transformer_id"
                pattern="[a-zA-Z0-9:_-]{1,32}"
                maxLength={32}
                placeholder="e.g. T-150"
                className={inputClass}
              />
            </label>
            <label>
              Rated capacity (kVA)
              <input required type="number" name="rated_kva" min="0.1" step="any" className={inputClass} />
            </label>
            <label>
              Transformer latitude
              <input required type="number" name="lat" min={-90} max={90} step="any" className={inputClass} />
            </label>
            <label>
              Transformer longitude
              <input required type="number" name="lon" min={-180} max={180} step="any" className={inputClass} />
            </label>
            <details className="sm:col-span-2">
              <summary className="cursor-pointer text-sm font-medium">Optional estimates</summary>
              <div className="mt-3 grid gap-4 sm:grid-cols-2">
                <label>
                  Estimated homes served
                  <input type="number" name="homes" min={0} step={1} defaultValue={0} className={inputClass} />
                </label>
                <label>
                  Metered home coverage (%)
                  <input
                    type="number"
                    name="coverage_percent"
                    min={0}
                    max={100}
                    step="any"
                    defaultValue={0}
                    className={inputClass}
                  />
                </label>
              </div>
            </details>
            <label className="text-sm sm:col-span-2">
              <input type="checkbox" name="simulated" /> Simulated transformer
            </label>
            <div className="flex flex-wrap gap-2 sm:col-span-2">
              <Button disabled={addTransformer.isPending}>
                {addTransformer.isPending ? "Adding…" : "Add transformer"}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setShowAddTransformer(false);
                  addTransformer.reset();
                }}
              >
                Cancel
              </Button>
            </div>
            {addTransformer.isError ? (
              <p role="alert" className="sm:col-span-2">
                {addTransformer.error.message}
              </p>
            ) : null}
          </form>
        </Card>
      ) : null}
      <Card className="mt-6 p-6 shadow-none">
        <h2 className="text-lg font-semibold">Home device totals</h2>
        <p className="text-sm text-muted-foreground">
          This adds up readings from home sensors assigned to the selected transformer. It shows those homes’ combined
          use, not a reading taken from the transformer itself.
        </p>
        <label>
          Transformer these devices are assigned to
          <select value={transformer} onChange={(e) => setTransformer(e.target.value)} className={inputClass}>
            <option value="">Select a transformer</option>
            {transformers.data?.map((t) => (
              <option key={t.transformer_id}>{t.transformer_id}</option>
            ))}
          </select>
        </label>
        {totals.isFetching && <p role="status">Refreshing readings…</p>}
        {totals.isError && (
          <p role="alert">
            Could not load readings. <button onClick={() => void totals.refetch()}>Try again</button>
          </p>
        )}
        {totals.data && (
          <>
            <p>{totals.data.registered_homes} registered households · Last 48 hours · 15-minute intervals</p>
            <p className="text-sm text-muted-foreground">
              Measured homes only. Missing reports are not zero usage. Totals include any labeled simulated readings.
            </p>
            <Link to={`/engineer/transformers/${encodeURIComponent(transformer)}`}>
              View transformer risk and forecast
            </Link>
            {!totals.data.points.length ? (
              <p>No readings received in the last 48 hours.</p>
            ) : (
              <div className="max-h-96 overflow-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr>
                      <th className="py-3">Time</th>
                      <th>Load</th>
                      <th>Energy</th>
                      <th>Reporting</th>
                    </tr>
                  </thead>
                  <tbody>
                    {totals.data.points.map((p) => (
                      <tr className="border-t" key={p.ts}>
                        <td className="py-3">
                          {new Date(p.ts).toLocaleString()}
                          <SimulatedLabel show={p.is_simulated} />
                        </td>
                        <td>{p.measured_kw.toFixed(2)} kW</td>
                        <td>{p.energy_kwh.toFixed(2)} kWh</td>
                        <td>{p.homes_reporting} homes</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </Card>
    </section>
  );
}

# SILIP Household Android app

Native Android app using Kotlin and Jetpack Compose. ABaKaDa is the implementation baseline for Gradle, Compose, and Material 3 patterns; its product content and branding are not copied.

## Product direction

SILIP helps household users understand energy costs, build safer electricity habits, and learn how opt-in household data can support grid planning. The app uses Ali the Alitaptap as its guide.

## Current redesign

The four primary destinations are Home, Usage, Learn, and Grid events. Home opens with Ali and a compact seven-day estimated cost, away reminders, and the next lesson. Usage opens with an interactive chart: choose seven days or 24 hours, switch kWh/pesos, and inspect exact dated values. Both read the separate mobile PoC Lambda and show data provenance and sensor freshness. Settings is reached from the top bar and stores the name, device ID, and theme on this phone. Learn retains its original illustrated learning map, five-question practice, and local progress. Grid events offers an expandable, explicitly illustrative example. Technical reading details and unit explanations are on Usage. Home and Usage estimate energy cost using a dated Meralco residential benchmark or the rate from your own bill. Usage adds a validated-against-baseline daily demand forecast and saving scenarios. Home offers manual away mode, opt-in geofenced reminders, and a separate solar journey with daytime-use analysis, a what-if slider, a preparation checklist and Meralco guidance. Events and payouts remain concepts.

See [the UI foundation](docs/ui-foundation.md) for the palette, screen jobs, product-language limits, and accessibility decisions. See [the Ali mascot guide](docs/mascot-guide.md) for pose usage. The [roadmap](docs/roadmap.md) and local Markdown tickets in `docs/tickets/` track the next steps.

## Current scaffold

- Compose app shell with Home, Usage, Learn, and Grid events destinations.
- SILIP palette in light and dark Material 3 themes.
- Local five-question lessons with answer feedback.
- Read-only calls to `/mobile-api/v1/devices/{clamp_id}/usage` through CloudFront, served by a separate Lambda querying Neon.
- Locally saved device ID plus loading, not-found, simulated-data, and network-error states.
- `INTERNET` and notification permissions plus a home-safety notification channel.

The dev mobile PoC endpoint permits only the allowlisted `silip-esp32-test` ID; prod's allowlist is empty. It has no household sign-in; do not enable more IDs or use it for real households until user authorization is added. The response excludes exact location and household identifiers.

The IoT device continues to POST to `/api/v1/devices/{clamp_id}/readings` with its device key. The Android app uses the separate mobile Lambda's read-only endpoint; it never receives the IoT device key or database credentials.

See [household energy features](docs/household-energy-features.md) for the rate source, model, opt-in alert setup, timing limits and focused tests.

The current clamp measures whole-home current. Appliance-level NILM, heat/micro-arc safety alerts, live bill forecasts, transformer demand-response events, and GCash payments need validated data/services before they can be presented as live capabilities.

## Build

Open this directory in Android Studio or run:

```sh
./gradlew assembleDebug
```

The debug build defaults to the current SILIP dev CloudFront domain. Override it with:

```sh
./gradlew assembleDebug -PsilipApiBaseUrl=https://your-cloudfront-domain
```

The package name `com.alventur.silipapp` is provisional.

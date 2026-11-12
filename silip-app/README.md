# SILIP Household Android app

Native Android app using Kotlin and Jetpack Compose. ABaKaDa is the implementation baseline for Gradle, Compose, and Material 3 patterns; its product content and branding are not copied.

## Product direction

SILIP helps household users understand energy costs, build safer electricity habits, and learn how opt-in household data can support grid planning. The app uses Ali the Alitaptap as its guide.

## Current redesign

The four primary destinations are Home, Usage, Learn, and Rewards. Home leads with an illustrative peso-per-hour estimate and budget progress; Usage presents the bill forecast and sample insights; Learn contains short lessons with five-question quizzes; Rewards explains a possible opt-in grid-response program. Sample values, appliance insights, safety detection, and payouts are clearly marked as previews because those services are not connected.

See [the UI foundation](docs/ui-foundation.md) for the palette, screen jobs, product-language limits, and accessibility decisions. See [the Ali mascot guide](docs/mascot-guide.md) for pose usage. The [roadmap](docs/roadmap.md) and local Markdown tickets in `docs/tickets/` track the next steps.

## Current scaffold

- Compose app shell with Home, Usage, Learn, and Rewards destinations.
- SILIP palette in light and dark Material 3 themes.
- Local five-question lessons with answer feedback.
- Household API models and endpoint contracts for `/api/v1/me/usage` and `/api/v1/me/device`.
- `INTERNET` and notification permissions plus a home-safety notification channel.

Cognito sign-in, HTTP serialization/transport, live API wiring, geofences, runtime permission prompts, and Firebase Cloud Messaging are not connected. Household API calls need a Cognito access token. The native app should use an OAuth authorization-code flow with PKCE; never embed an app-client secret or AWS credentials.

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

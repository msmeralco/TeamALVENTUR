# SILIP Household Android app

Native Android app scaffold using Kotlin and Jetpack Compose. Abakada is the implementation baseline for Gradle, Compose, and Material 3 patterns; its product content and branding are not copied.

## Product direction

- Online household status and usage from the SILIP API.
- Short lessons, practice activities, progress, and points inspired by language-learning apps.
- Optional home-exit safety checklist reminders.
- The app can prompt a checklist when the user leaves home. The existing whole-home clamp does not identify which appliance is on; appliance-specific alerts need additional sensors.

## UI foundation

The app follows the screen and interaction patterns in ABaKaDa while using SILIP's energy context and green visual language. It has a four-tab shell, a household connection card, a learning-path summary, lesson cards, a one-question practice flow with submitted-answer feedback, and a My home explanation of the whole-home sensor. Ali the Alitaptap appears in section-specific guidance cards and practice feedback. See [the Ali mascot guide](docs/mascot-guide.md) for pose and color usage.

See [the UI foundation](docs/ui-foundation.md) for design tokens, screen structure, accessibility decisions, and the current integration boundary.
See the [roadmap](docs/roadmap.md) and its individual Markdown tickets in `docs/tickets/` for the next implementation steps.

## Current scaffold

- Compose app shell with Home, Learn, Practice, and My home tabs.
- SILIP green-accented light and dark themes with rounded category surfaces.
- A small practice flow with answer selection, submit, feedback, and retry.
- `INTERNET` and notification permissions.
- API base URL configuration through `BuildConfig.API_BASE_URL`.
- Household API models and endpoint contracts for `/api/v1/me/usage` and `/api/v1/me/device`.
- A home-safety notification channel.

Cognito sign-in, HTTP serialization/transport, geofence registration, runtime permission prompts, and Firebase Cloud Messaging are not wired yet. Household API calls will need a Cognito access token. The native app should use an OAuth authorization-code flow with PKCE and a Cognito app client configured for its Android redirect URI; never embed an app-client secret or AWS credentials.

Use the CloudFront site origin as the API base URL, not the direct Lambda Function URL, which requires AWS signing. The debug build defaults to the current SILIP dev CloudFront domain. Override it with:

```sh
./gradlew assembleDebug -PsilipApiBaseUrl=https://your-cloudfront-domain
```

Lessons can be bundled or cached, while household status requires an internet connection. Before implementing home-exit reminders, request location access only after the user opts in and explain that location is used to trigger a checklist. The background-location permission is declared for that planned feature but is not requested by the scaffold.

## Build

Open this directory in Android Studio or run:

```sh
./gradlew assembleDebug
```

The package name `com.alventur.silipapp` is provisional.

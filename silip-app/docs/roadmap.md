# SILIP Android roadmap

The current UI is a consumer-focused preview shaped around the “Two Birds, One Stone” pitch: make household cost and safety easier to understand while teaching habits that can also support better grid planning. Ali the Alitaptap remains the app mascot. All cost, safety, appliance, and reward figures in the redesign are explicitly illustrative.

Individual work items live under [`tickets/`](tickets/). They are local Markdown tickets, not GitHub issues.

## Suggested order

### 1. Household access and live data

1. [Define household onboarding and device-linking](tickets/01-household-onboarding.md)
2. [Connect Cognito and the household API](tickets/02-cognito-household-api.md) — after ticket 01

The API resolves the household server-side from the Cognito subject. Keep household identifiers such as `sin_hash` out of the app. Wire live usage and device state before replacing the demo labels or sample values.

### 2. Learning experience

3. [Persist lesson completion and rewards](tickets/03-learning-progress.md)
4. [Build multi-step lessons and practice](tickets/04-lessons-practice-flow.md) — use ticket 03's progress model

Learning content can work offline; household telemetry cannot.

### 3. Reminders and supported alerts

5. [Add opt-in home-exit checklist reminders](tickets/05-home-exit-reminders.md)
6. [Deliver supported household alerts through push](tickets/06-push-alerts.md) — after API/product confirms event types and thresholds

The current clamp measures whole-home current. Do not claim heat, micro-arcing, or a named appliance alert without validated hardware and detection support.

### 4. Brand and quality

7. [Integrate SILIP mascot artwork](tickets/07-silip-mascot.md) — complete; see [the Ali mascot guide](mascot-guide.md)
8. [Review accessibility and adaptive layouts](tickets/08-accessibility-adaptive-layout.md)

### 5. Pitch features that need new services

- Validate NILM before showing appliance health, degradation, or phantom-load findings as household facts.
- Confirm the tariff and calculation inputs before presenting a bill forecast as an estimate for a specific account.
- Define opt-in, transformer event thresholds, verification, payout partner, and consent before enabling demand-response rewards.
- Validate electrical safety-alert hardware and event handling before describing alerts as fire or micro-arc detection.

## Current limits

- The Home/Usage screens show a demo household with sample peso and kW values.
- Cognito sign-in, HTTP transport, and Compose integration with `HouseholdApi` are not wired.
- Lesson completion, XP, streaks, leaderboard, geofences, notifications, NILM, safety detection, and payouts are not live.

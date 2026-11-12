# SILIP Android roadmap

The current UI foundation adapts ABaKaDa's navigation and learning interactions to SILIP's household-energy context. The app has Home, Learn, Practice, and My home sections; a green Material 3 theme; Ali the Alitaptap across the screen and feedback states; household connection states; starter lessons; and one answer-feedback practice check.

Individual work items live under [`tickets/`](tickets/). They are local Markdown tickets, not GitHub issues.

## Suggested order

### 1. Household access and live data

1. [Define household onboarding and device-linking](tickets/01-household-onboarding.md)
2. [Connect Cognito and the household API](tickets/02-cognito-household-api.md) — after ticket 01

The API currently resolves the household server-side from the Cognito subject. Keep household identifiers such as `sin_hash` out of the app.

### 2. Learning experience

3. [Persist lesson completion and rewards](tickets/03-learning-progress.md)
4. [Build multi-step lessons and practice](tickets/04-lessons-practice-flow.md) — use ticket 03's progress model

Learning content can work offline; household telemetry cannot.

### 3. Reminders and alerts

5. [Add opt-in home-exit checklist reminders](tickets/05-home-exit-reminders.md)
6. [Deliver supported household alerts through push](tickets/06-push-alerts.md) — after API/product confirms event types and thresholds

Treat a location-triggered message as a checklist prompt. The current sensor measures whole-home demand and cannot name an appliance left on.

### 4. Brand and quality pass

7. [Integrate SILIP mascot artwork](tickets/07-silip-mascot.md) — done; see [the mascot guide](mascot-guide.md)
8. [Review accessibility and adaptive layouts](tickets/08-accessibility-adaptive-layout.md)

## Current limits

- Household status is not connected to Cognito or live API data yet.
- Lesson completion, XP, and streaks are not persisted yet.
- The practice screen has one starter question.
- Geofences, local notifications, and Firebase Cloud Messaging are not wired in.

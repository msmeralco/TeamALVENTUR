# SILIP Android UI foundation

SILIP is a household electricity companion for people who want to understand costs, make safer choices, and learn practical energy habits. The primary screen job is to answer: “What is happening in my home, what might it cost, and what should I do next?”

PoC readings are loaded from a separate mobile Lambda. Appliance-level inference, safety alerts, and rewards remain previews until their data services and hardware support are connected.

## Visual direction

The design uses the palette supplied for SILIP. The firefly remains **Ali the Alitaptap**; the “Rosa” household and values in the redesign are illustrative examples from the pitch.

Use Ali on the left as the learner avatar and guide, following the existing Abakada mascot pattern. Keep headings and helper text brief. Learn uses a game map with a streak/XP row, unit banner, winding lesson route, bonus chest, and trophy. Correct answers unlock the next lesson; completed lessons stay open for retakes. XP is awarded once per lesson. Progress is saved on-device for the preview and is not synced to a user account. The interaction pattern takes inspiration from Duolingo’s short lessons and visible progression, while retaining SILIP’s palette and household-energy content.

| Token | Hex | Use |
| --- | --- | --- |
| Charcoal | `#262626` | Main text and dark-mode background |
| Sage | `#C3D2C5` | Soft cards, progress tracks, and selected states |
| Paper | `#F2EFE3` | Light-mode background and text on deep green |
| Moss | `#58815F` | Supporting charts and secondary green |
| Forest | `#254E21` | Primary actions, selected navigation, and energy receipt |
| Alert orange | `#9C4A0B` | Caution states only, paired with text or an icon |

Headings and explanations use the Android sans-serif family. Readings such as pesos and kW use monospaced numerals so values align like an instrument display. Body text stays at 16 sp or larger where practical, with 4/8 dp spacing increments and 48 dp minimum touch targets.

## Navigation and screen jobs

| Destination | Job |
| --- | --- |
| Home | Show a cost estimate, budget progress, safety-data limits, and a next learning action |
| Usage | Explain a month-end estimate and show example load, phantom-load, and appliance-health insights |
| Learn | Offer short electricity lessons with five-question practice quizzes |
| Rewards | Explain a possible opt-in grid-response program and its data/reward steps |

The quick challenge is a sub-flow of Learn, not a separate bottom-navigation destination. On larger screens, content is centered at a readable maximum width; on phones it uses 20 dp side gutters.

## Signature component: energy receipt

Home and Usage show the selected device's seven-day energy total, recent kW trend, transformer assignment, last-seen time, and simulated-data status from the mobile API. Peso estimates and bill forecasts remain illustrative because a tariff-aware calculation is not available yet.

## Truthful product language

- The SCT-013 current clamp reports total current/demand for the circuit. It does not identify a flat iron, measure heat, or independently detect micro-arcing.
- A peso estimate needs a valid voltage/power calculation, a current tariff, and real household readings. The figures in this UI are sample values.
- Appliance health and phantom-load insights require validated NILM/signature analysis. The screens call these examples or development previews.
- Grid-response offers, neighborhood participation, wallets, and GCash payouts are concepts only. No event, consent flow, or payment service is connected.
- “No alert” must never be described as “safe” when the sensor or account is disconnected.

## Accessibility and interaction

Use text and icon labels alongside color, hide decorative Ali artwork from TalkBack, and give icon-only controls meaningful descriptions. Keep headings semantic, preserve scroll space above the bottom navigation, support system font scaling, and use native Material buttons/cards for touch feedback. The paper/sage/forest palette has light and dark mappings; verify actual contrast and layouts on devices before release.

## Learning game assets

The map uses original transparent assets: `silip_energy_token.png`, `silip_reward_chest.png`, and `silip_trophy.png`. They accompany tappable/locked lesson nodes and previews of future rewards.

## Mascot

Ali appears at the left of page headers, lesson guidance, safety and insight cards, and answer feedback. Emerald bulb poses support welcoming/learning/correct states; orange is reserved for caution. The image never communicates a device status by itself. See [the Ali mascot guide](mascot-guide.md).

## Current implementation boundary

- The Android PoC accepts a device ID and calls the separate `/mobile-api/v1/devices/{clamp_id}/usage` Lambda route through CloudFront.
- The dev mobile route is allowlisted to `silip-esp32-test`; prod's allowlist is empty. It returns aggregate usage and transformer ID, but no exact location or household identifier. Add user authorization before exposing real households or additional device IDs.
- The existing `/api/v1/devices/{clamp_id}/readings` POST route remains the IoT ingestion path and still requires `X-Device-Key`.
- Bill calculations and appliance-level insights still use preview content; only whole-home usage and device metadata are live.
- Household readings, bill calculations, persisted learning progress, notifications, geofences, NILM, micro-arc detection, and demand-response payouts are not live.
- Lesson quizzes run locally; the preview stores completion, streak, and XP on-device. Leaderboards and reward redemption are not implemented.

Use the [roadmap](roadmap.md) and local Markdown [tickets](tickets/) to sequence implementation work.

## Visual clarity pass — 13 November 2026

Home leads with seven-day household energy and daily bars, then one action from Ali and the next lesson. Short labels accompany every meaningful icon. Detailed device identifiers, interval counts, and measurement limits are behind Usage's reading-details disclosure. Simulated usage and sensor freshness stay visible beside the headline data. Daily bars use the API's quarter-hour averages; boundary days may be partial, and the window is anchored to stored data rather than today's date.

The four bottom destinations are Home, Usage, Learn, and Grid events. Settings moves to the top bar; system Back returns to the previous destination. Learn retains its previous winding map, energy-token nodes, reward artwork, labels, and palette. Grid events has an expandable example and an explicit demo label.

This applies chunking and progressive disclosure to reduce reading, familiar navigation to make actions discoverable, and visible progress to clarify the next lesson. Icons support short text labels because unfamiliar symbols alone would increase the effort to understand the app. Ali's existing poses and the green Material theme provide continuity. Android's disabled-animation preference suppresses Ali's decorative motion.

This pass changes presentation and navigation. Ownership verification, tariff-based cost estimates, stable lesson-ID progress, date-based streaks, new solar/EV content, and real event verification remain the work packages described in the product realignment plan.

## Home versus Usage — distinct entry views

Home is Ali's companion dashboard: greeting, compact seven-day estimated cost, sensor freshness, a route to the usage breakdown, away reminders, and the next lesson. It contains no historical chart or rate-editing form. Usage starts with the data explorer: seven days or the latest 24 stored hours, energy/cost selection, calendar-date or four-hour group bars, and exact selected values. Earlier/Later buttons provide an alternative to tapping narrow chart bars. Forecasts, saving insights, rate calculation and technical details follow the explorer.

This prioritizes one next action on Home and analysis on Usage, applying selective attention and progressive disclosure. The first viewport must look different when switching tabs: Ali and a green summary on Home; a white analytical chart and period controls on Usage. The previous Learn layout and palette remain intact. Both destinations keep simulated-data and stale-sensor labels visible, and chart windows use the data's own clock.

## Delight redesign: flows, truth labels and motion (13 November 2026)

### New flows

| Flow | Where | Notes |
| --- | --- | --- |
| Onboarding | `ui/onboarding/OnboardingFlow.kt` | Splash, three value cards (pager with a stretching dot indicator), chip personalization with Ali's replies, connect clamp or Rosa's demo home with an install diagram, permission priming, celebration. "Skip" saves answers so far, fills the rest with defaults and opens the demo home on first run. "Replay intro" in Settings keeps all progress and does not award XP twice. |
| Home | `ui/home/HomeScreen.kt` | Previous Home content plus an Eco-Streak and quiz card. Opens the safety alert sheet when Settings sends the sample alert. |
| Safety alert | `ui/alerts/SafetyAlertSheet.kt` | Bottom sheet: "I checked, all good", "Call someone at home" (opens the dialer with no number; nothing is stored), "Remind me in 10 min". Ali turns green with "Thanks for checking." |
| Daily quiz | `ui/learn/DailyQuiz.kt` | One question per Manila day from the lesson quizzes. Answering counts today for the streak. |
| Leaderboard | `ui/learn/Leaderboard.kt` | Demo neighborhood of 8 neighbors plus "You" (your on-device XP). |
| Grid events | `ui/grid/GridEventScreen.kt` | Demo April-night Grid Alert: transformer load drops as households join, shown as a percentage and a word. |

The bottom bar keeps Home, Usage, Learn and Grid events. The selected icon fills and springs up and its label turns bold. Settings stays in the top bar.

### Truth labels

- The clamp measures whole-home current. The safety alert says: "A steady 1.1 kW load has been on for 40 min while you're away (away mode on). Did someone leave something plugged in, like an iron?" Never "heat signature" or an appliance claim.
- Peso figures are estimates: kW × the dated Meralco rate in `energy/EnergyAnalysis.kt`, or the user's bill rate (`burnRatePhpPerHour`). Label them "estimate".
- The monthly budget is a goal (10% below the last-bill answer), not a forecast.
- Demo content carries a visible label from `DemoLabels`: "Simulated" for Rosa's readings and the sample alert, "Demo neighborhood" for the leaderboard, "Pilot preview" for grid events and rewards. No payment, consent or event service exists.
- The install explainer says the clamp is fitted after the meter by a licensed electrician and never touches Meralco's meter, seal or service drop.
- No alert never means safe. An offline clamp says so.

### Motion rules

- Tokens live in `ui/design/Motion.kt`: 150 ms short, 250 ms standard, 300 ms entering, 700 ms counters. Routine UI changes stay at or under 300 ms.
- Springs are for playful moments only: Ali, the streak pop, XP, the nav icon and the pager indicator.
- One orchestrated moment per screen. Onboarding's splash fly-in and the celebration confetti are the peaks.
- `rememberReduceMotion()` reads Android's animator duration scale. When it is 0, Ali is drawn still, glows and flickers stop, confetti is skipped and state changes snap.
- Ali is decorative to TalkBack. Animated numbers announce only their final value. Color always comes with words.

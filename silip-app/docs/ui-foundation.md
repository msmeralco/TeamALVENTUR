# SILIP Android UI foundation

SILIP is a household electricity companion for people who want to understand costs, make safer choices, and learn practical energy habits. The primary screen job is to answer: “What is happening in my home, what might it cost, and what should I do next?”

The current app is a front-end preview. Household readings, appliance-level inference, safety alerts, and rewards must not be presented as live until their data services and hardware support are connected.

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

The Home screen leads with a deep-green card showing an illustrative hourly peso estimate, a sample kW load, and a compact load trend. This connects an abstract current reading to the consumer’s bill. Values carry a sample-data label and explanatory copy; they are not fetched from the household API yet.

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

- The UI uses a demo household and illustrative energy values.
- Cognito sign-in, HTTP transport, and connection of the Compose screens to `HouseholdApi` are not implemented.
- Household readings, bill calculations, persisted learning progress, notifications, geofences, NILM, micro-arc detection, and demand-response payouts are not live.
- Lesson quizzes run locally; the preview stores completion, streak, and XP on-device. Leaderboards and reward redemption are not implemented.

Use the [roadmap](roadmap.md) and local Markdown [tickets](tickets/) to sequence implementation work.

# SILIP Android UI foundation

This document records the first SILIP Android UI decisions. The screen layout and interaction patterns draw from the ABaKaDa app, while the colors, copy, and content model are tailored to household energy awareness. ABaKaDa's child-rights content, branding, and mascot assets are not part of SILIP.

## Product shape

SILIP combines two different jobs:

- Help a household user understand current whole-home readings from the SILIP service.
- Teach safer, more responsible electricity habits through short lessons and practice.

Live household information needs an internet connection and an authenticated account linked to a registered SILIP device. Lessons may be available on-device. An outage or disconnected account must never be displayed as zero usage or as a safe reading.

## Navigation

The persistent four-destination bar follows ABaKaDa's simple navigation model:

| Destination | SILIP purpose |
| --- | --- |
| Home | Household connection summary, today's learning, and shortcuts |
| Learn | Short lessons organized into a visible learning path |
| Practice | Scenario questions with progress and answer feedback |
| My home | Live household readings, sensor explanation, and reminder information |

Keep detail flows within these sections. Add a new top-level destination only when it represents a distinct recurring user goal.

## Screen patterns

- **Home:** welcoming guide panel, truthful household state, one learning-path card, then a two-column grid of icon-led actions.
- **Learn:** a path summary followed by grouped lesson cards. Show time and reward as supporting metadata, and make completion progress explicit once it is persisted.
- **Practice:** show progress, selectable answer cards, and feedback only after an answer is submitted. Give the user a clear retry path.
- **My home:** distinguish current account/device connection state from measured household demand. Explain what the installed current sensor can and cannot identify.

Use scrollable, content-first layouts with 20 dp side gutters, 4/8 dp spacing increments, rounded Material 3 cards, and touch targets of at least 48 dp. Use the system sans-serif typography and let text wrap at larger font sizes.

## Visual tokens

| Role | Light theme | Use |
| --- | --- | --- |
| Forest green | `#146B4A` | Primary action and selected navigation |
| Soft leaf | `#D3F2DF` | Welcome and learning surfaces |
| Slate blue | `#416779` | Information and practice surfaces |
| Soft blue | `#D6EAF2` | Supporting information |
| Deep amber | `#715300` | Pending or not-connected state |
| Soft amber | `#FCECC2` | Non-error caution state |
| Deep coral | `#8F3F3B` | Error or incorrect-answer state |
| Warm paper | `#F5F8F4` | App background |
| Ink | `#17211B` | Main text |

Semantic status must also use text or an icon; color alone is not enough. The dark palette keeps the same status meanings with readable contrast.

## Mascot guide

Ali the Alitaptap appears in a mascot-and-guidance-bubble header on Home, Learn, Practice, and My home, following the ABaKaDa guide-card pattern. Emerald-bulb poses are used for welcome, learning, household checking, and correct feedback; the orange-bulb pose is reserved for caution feedback. See [the Ali mascot guide](mascot-guide.md) for pose mapping and color use. Keep the mascot decorative to TalkBack; visible text must communicate the same guidance.

## Sensor and alert language

The current split-core sensor provides a whole-home current reading. It does not identify individual appliances. Therefore:

- Show unavailable, stale, loading, and connected states separately; never invent a reading.
- Describe an exit notification as an optional checklist prompt unless a future sensor can actually identify a particular appliance.
- Only describe an alert as appliance-specific when the measured data and service support that claim.
- Ask for location permission only after the user opts into a home-exit reminder, with an explanation of the trigger.
- Keep user-controlled notification preferences and make account/data boundaries visible.

## Current boundary

The current UI is a visual and interaction foundation. Household cards are not yet connected to Cognito or live API data. Lesson completion, XP, and streaks are not persisted. The practice screen currently contains one starter check. Geofencing and local/remote notifications are not wired in this pass. Follow-up tickets track those integrations.

## ABaKaDa patterns reused

- Persistent four-tab navigation and content grouped inside each section.
- Scroll-first home and lesson screens with native Compose surfaces.
- Rounded, category-tinted home tiles with icons beside readable text.
- Visible step progress, selectable answer cards, and a separate feedback state.
- A section-specific mascot pose beside a short guidance bubble.
- System type, accessible tap areas, semantic headings, and non-color status cues.

The education path is inspired by short, rewarding lessons; SILIP uses energy-use learning goals and does not copy ABaKaDa's subject matter, UI branding, or mascot.

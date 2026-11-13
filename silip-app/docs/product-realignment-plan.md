# SILIP mobile product realignment

Prepared 13 November 2026. Source review of the Android app, its API client, lesson catalog, and product docs. This is a product plan; no device walkthrough or timed usability study was performed.

## Product brief

**Purpose:** Ali helps households understand electricity costs, build smarter and more responsible energy habits, learn about solar and electric vehicles, and voluntarily support their local grid.

**Primary user:** A household decision-maker like Aling Rosa who wants to avoid an unexpected bill and know what action is worth taking today. Cost anxiety is the working hypothesis from the team’s brief; interviews must establish its frequency, severity, and current workarounds.

**Secondary beneficiary:** An engineer like Paolo who needs better visibility into changing local demand. The engineer uses the web dashboard. The mobile app earns household participation by delivering useful household outcomes.

**Product thesis:** Understand → take a useful action → see the result → learn why → choose whether to contribute. Household value should work even when no grid event is available.

**Why now:** The team already has an IoT ingestion path, a mobile whole-home usage endpoint, a transformer dashboard, and Ali’s learning experience. These are assets for testing the thesis, not evidence of consumer adoption or verified predictive accuracy.

**Long-term experience:** Rosa sees a credible cost outlook, receives actionable advice based on supported data, develops energy knowledge, and joins optional grid events with transparent verification and rewards. Paolo sees demand estimates with coverage and uncertainty, and can evaluate the effect of coordinated household actions.

**MVP:** One connected household sees fresh usage and an explicitly qualified cost estimate, completes a relevant learning/action loop, explores solar or EV basics, and can experience a clearly identified demo grid event. This proves the experience before introducing real payout obligations or safety claims.

**Recommendation:** Proceed with this focused MVP. Validate household value before expanding the game, appliance inference, or payment infrastructure. There is no adoption, retention, willingness-to-pay, or utility partnership evidence in this source scan from which to claim product-market fit.

## What exists today

| Area | Source evidence | Gap against the goal |
| --- | --- | --- |
| Home | `SilipApp.kt` renders a device-ID entry, usage card, safety preview, and lesson action | First interaction is technical; cost and next action are not the core experience |
| Usage | Reuses whole-home data and shows a trend plus concept cards | Does not yet explain estimated pesos, billing cycle, or meaningful before/after changes |
| Telemetry | `HttpHouseholdApi.kt` returns device ID, transformer, last seen, seven-day kWh, and kW points | No tariff, voltage/power-factor provenance, live subscription, or forecast contract |
| Refresh | Fetch runs on device connection or manual refresh | “Watch your burn rate change live” is not implemented |
| Access | Demo device defaults to `silip-esp32-test`; README describes a public allowlist | Device ID is not proof of household ownership; real rollout needs authenticated linking |
| Learn | Four topics: standby power, cooling, bill basics, leaving home; five-question quizzes | Solar, EVs, contextual recommendations, and a separate 15-second daily question are absent |
| Progress | Local SharedPreferences save XP and completion count | Progress is positional rather than lesson-ID based; inserting lessons could change its meaning |
| Streak | Completion applies `maxOf(streakDays, 1)` | No date-based consecutive-day streak; it cannot grow beyond one from a new profile |
| Rewards | Optional grid partnership is described through preview cards | No event state, consent, verification, earnings ledger, or payment service |
| Ali | Multiple poses already support guidance and feedback | Needs a consistent role explaining evidence, action, and outcome across screens |
| Documentation | README and Android client now use `/mobile-api/v1/devices/{clamp_id}/usage` | Deploy the separate mobile Lambda and CloudFront behavior so the documented route exists in the target environment |

`BillForecastCard()` contains a sample projection but is not called by the reviewed Home/Usage flows. Existing docs also conflict about whether learning progress is persisted; code currently persists it locally. Resolve these discrepancies while updating the roadmap.

## Align the promises with evidence

| Pitch promise | Product direction |
| --- | --- |
| Instant pesos and predicted bill | Start with estimated energy cost, measured time window, rate source/date, and assumptions. Separate current run-rate from accumulated cost and a future bill forecast. Avoid implying the estimate is Meralco’s official bill. |
| “Heat signature” or a named flat iron detected | A current clamp does not directly measure heat or identify an appliance. Develop sustained unusual-demand notices only after validating detection and false positives. Ask users to check usage; do not claim a fire was detected or prevented. |
| “Will fail by 10 PM” | Demonstrate an elevated overload-risk forecast with horizon, coverage, and confidence. Failure probability and exact failure timing require separate outcome data and calibration. |
| All transformer load measured | Explain which homes report, what is measured versus estimated, and how assignment/coverage affects confidence. Household opt-in coverage does not establish a complete transformer measurement. |
| Automatic demand response and ₱50 GCash | Demo a scenario with an example incentive. Real offers need an authorized program, participation terms, baseline, verification, funding, and payment integration. Load reduction during one event is active participation, not guaranteed passive income. |

Current-only sensing also limits accurate real-power calculation and solar import/export interpretation. Audit the full measurement chain before relying on reported kWh for cost or event verification. [OpenEnergyMonitor’s AC measurement guidance](https://docs.openenergymonitor.org/electricity-monitoring/ac-power-theory/advanced-maths.html) explains voltage/current sampling, real power, and power factor.

EVs are electric transport, not renewable generation. Teach how charging demand and timing interact with the grid and available solar. Solar education should explain self-consumption, variable generation, and eligible export credits. Use maintained local sources such as [Meralco’s Solar and Net Metering guidance](https://www.meralco.com.ph/residential/energy-solutions/solar-and-renewables/solar-net-metering); avoid universal savings or payback promises.

## Proposed application experience

Keep four destinations: **Home, Usage, Learn, Grid events**. Put earnings inside Grid events so a future payment feature does not dominate the app before participation works.

### Home: “What should I know and do today?”

1. Lead with estimated cost for a clear period, or a useful usage state when cost inputs are unavailable. Show freshness and device connection alongside the value.
2. Ali offers one specific next action with its reason. Example: “Your evening use was higher than your recent evenings. Review the trend.” Personalization requires enough comparable history.
3. Surface a supported alert or active event when relevant. Give it clear priority without placing permanent warning previews above everyday value.
4. Offer one optional daily question or next lesson. Use a compact progress cue.

New users can explore learning before owning a sensor. Connecting a household should use a guided claim/QR flow backed by ownership verification; retain manual entry as a recovery path. Ask about billing period, budget, interests, solar, and EV ownership only when needed for a feature.

### Usage: “Why might my cost change?”

Show current demand, interval history, estimated cost, and comparable periods. Explain units in place: kW is the current rate; kWh is energy over time; pesos are calculated under stated assumptions. Let a user annotate an action such as changing cooling settings, then compare suitable periods without asserting causation. Add budget outlook only after enough billing-cycle data exists.

### Learn: “Help me make a better energy decision.”

Use short selectable learning paths. Recommend a next topic while leaving relevant content discoverable:

| Path | Topics | Practical outcome |
| --- | --- | --- |
| Know my bill | kW vs kWh, rate assumptions, billing cycles, budgets | Read a usage/cost change correctly |
| Smarter everyday habits | Cooling, standby use, appliance labels, practical checklists | Choose one feasible habit and review its result |
| Solar basics | Daytime use, generation variability, self-consumption, net metering, batteries | Know which questions to ask a qualified installer |
| EV basics | Charging energy, charging power, scheduling, range needs, solar charging | Plan charging around required travel and household constraints |
| Help our grid | Peak demand, transformer coverage, consent, grid events, verification | Understand and choose whether to join an event |

Each lesson follows **explain → one decision → feedback → optional real-world action → reflection**. Retain longer practice quizzes as a separate mode; the morning interaction should be one genuinely brief question. Award learning points for demonstrated learning; label self-reported actions separately from measured outcomes.

Give lessons stable IDs, date-based completion events, and a progress model that supports curriculum changes. Save progress offline and synchronize after account support exists. Streaks should respect local dates and voluntary participation; reminders, leagues, and public visibility remain optional. Avoid leaderboards based on absolute low consumption, which would unfairly compare households with different needs.

### Grid events: “What is being asked, and what happens afterward?”

Make the event lifecycle visible: **invited → accepted/declined → active → verifying → completed or unable to verify**. Present timing, requested action, measurement method, eligibility, example/actual incentive, and the ability to decline. Never encourage users to turn off essential loads.

During an event, show current status and data freshness. Afterward, show the measured result, verification status, and reward status as distinct facts. Missing telemetry must not become a successful reduction. Real rewards require a server-side ledger and payout states; a notification is neither proof of participation nor payment.

Ali’s role throughout is **observe → explain → suggest → acknowledge**. His language and appearance must agree with the evidence: learning success, supported caution, disconnected sensor, and demo event each have explicit text labels.

## UX decisions to apply

| Observed friction | Law | Proposed change | Check |
| --- | --- | --- | --- |
| Technical device input is the first household task | Jakob’s Law / Mental Models | Guided household connection with recognizable ownership confirmation | A first-time user can link the intended home without understanding backend identifiers |
| Home contains several competing concepts | Hick’s Law / Selective Attention | One primary value and one recommended action; alerts appear when relevant | Rosa can identify the next useful action without explaining the whole product |
| kW, kWh, cost, and prediction can blur together | Cognitive Load / Chunking | Group by question and time period; put assumptions beside estimates | Users distinguish measured usage from estimated cost |
| Long quizzes conflict with a 15-second habit | Goal-Gradient Effect / Flow | Separate one-question daily practice from lessons | Users finish the daily interaction and can explain its lesson |
| Progress risks becoming the purpose | Peak-End Rule | End lessons with an applicable choice and clear completion feedback | Users recall a useful action, beyond the XP earned |
| Joining a grid event has uncertain consequences | Tesler’s Law | Reveal the necessary consent and verification detail at the decision point | Users understand what they share, what they do, and when rewards qualify |

These are design hypotheses, not usability results. Validate them with representative users.

## Delivery sequence and priorities

ICE values are planning judgments on a 1–5 scale, not measured confidence. Effort is relative; assign calendar dates after team capacity and the demo deadline are confirmed.

| Priority | Work package | Impact | Confidence | Effort | ICE: I × C ÷ E | Completion evidence |
| --- | --- | --- | --- | --- | --- | --- |
| P0 | Confirm API route, units, freshness, measurement provenance, and demo data modes | 5 | 5 | 2 | 12.5 | One documented source contract; stale/missing/simulated states visible |
| P0 | Home’s usage/cost/action loop | 5 | 4 | 3 | 6.7 | User sees meaningful data and takes one useful next step |
| P0 | Protected household ownership and onboarding | 5 | 5 | 4 | 6.3 | Unauthorized households cannot be accessed; demo access remains explicit |
| P1 | Solar/EV learning paths plus one-question daily practice | 4 | 4 | 2 | 8.0 | New content works offline; users explain a relevant decision |
| P1 | Stable lesson progress and real date-based streaks | 3 | 5 | 2 | 7.5 | Reopening/curriculum updates preserve progress correctly |
| P1 | One coherent demo grid-event journey | 5 | 3 | 4 | 3.8 | Invitation through verification/result runs with visible demo provenance |
| P2 | Validated unusual-demand notifications | 4 | 2 | 4 | 2.0 | Detection performance and alert comprehension meet agreed thresholds |
| P2 | Real grid-event pilot and payout | 5 | 2 | 5 | 2.0 | Utility/program authorization, verified reductions, reconciliation, and funded payout |

Dependencies and risk override numeric rank: protecting real household access precedes expansion beyond the allowlisted PoC. Content can proceed alongside telemetry and onboarding work.

**First increment:** Complete the P0 source audit, document measurement assumptions, define the household first-win flow, and fix contradictory docs. Validate Home/Usage prototypes with users before expanding screens.

**Second increment:** Deliver contextual Ali guidance, cost estimates supported by verified inputs, renewable/EV education, and durable learning progress. Introduce reminders only with explicit preference controls.

**Hackathon demonstration:** Show one connected household action, a brief solar/EV lesson, then one clearly simulated event shared by the Android app and engineer dashboard. The existing web risk map and mobile feed may use different data sources; align transformer/device IDs, scenario time, readings, and provenance so the demonstration tells one consistent story. Show aggregate load changing, not an unsupported claim that a transformer cooled or a failure was prevented.

**Pilot increment:** Recruit consenting households, validate cost estimates against reference measurements/bills, assess advice comprehension, and evaluate grid-event baselines with the utility. Expand notification and payout scope only after those dependencies are satisfied.

Appliance identification, fire detection, exact failure timing, and automatic cash rewards remain separate research/partnership workstreams. They should not delay proving household comprehension, learning, and voluntary participation.

## Evidence and proposed success criteria

- **Primary outcome:** Weekly households completing a meaningful energy loop: inspect credible usage/cost information, choose an action or learning decision, and review the outcome. Report the steps separately to avoid inflating one combined number.
- **First value:** Measure time from app open to understanding one household reading and choosing a next action. Proposed prototype target: 4 of 5 participants complete this without coaching within two minutes after device linking. This is a usability checkpoint, not population evidence.
- **Learning:** Track lesson completion and a delayed transfer question about bills, solar, or EV charging. XP and streaks are engagement indicators, not proof of understanding or savings.
- **Trust:** Measure whether users correctly identify simulated values, stale readings, cost estimates, and verified rewards. Track misunderstood warnings and unnecessary alert burden.
- **Grid events:** Track invitation delivery, opt-in, completion, telemetry coverage, verified reduction versus a documented baseline, and payout reconciliation. Report estimates and verified outcomes separately.
- **Retention:** Measure repeat meaningful use over subsequent weeks, not just notification opens. Compare households with and without active events to test whether daily value stands on its own.

Next research: interview household decision-makers about bill surprises, preferred language, learning interest, feasible actions, data-sharing comfort, and reasons to ignore Ali. Run a task-based prototype review covering a stale sensor, a cost increase, a solar/EV lesson, and a declined grid event. Use the findings to adjust this plan before turning it into detailed engineering tickets.

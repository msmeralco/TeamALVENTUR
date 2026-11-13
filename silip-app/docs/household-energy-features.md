# Household cost, demand forecast, and away reminders

## Cost estimate

Home and Usage show the stored seven-day kWh multiplied by the selected rate. The default is Meralco's **October 2026 non-lifeline, 200 kWh/month benchmark: PHP 15.0615/kWh**. Source: [Residential Bills at Typical Consumption Levels](https://www.meralco.com.ph/uploads/documents/source-delta/2026-10-25/5afca4c86acee54e324a937c7481894500ae62aa0a92140d65f6a0e6ea943f79.pdf?v=1793354026), linked from [Meralco Rates & Charges](https://www.meralco.com.ph/residential/rates-and-charges). Checked 13 November 2026; that page's newest listed month was October 2026.

This is a dated benchmark approximation. It is not a tariff engine or an official bill: consumption level, billing period, LGU charges, refunds, discounts and measurement assumptions affect actual amounts. The bundled rate does not update automatically. Under “How is this calculated?”, users can enter the effective rate from their own Meralco bill or restore the published default. The selection is saved locally and applies to the forecast and saving scenarios too. Example: 71.16 kWh × PHP 15.0615 = PHP 1,071.78, rounded for display.

## Demand forecast and insights

Usage forecasts the next 96 quarter-hour points after the latest stored interval. It requires at least five days, 480 observations, and 80% overall coverage within an eight-day window. Invalid values are excluded, duplicates are averaged, and gaps are not filled during model training.

The candidate regression uses an intercept, scaled time trend, three daily Fourier harmonics and a weekend indicator, with a small ridge penalty. The latest 24 hours are held out. The candidate is compared against a previous-day pattern using mean absolute error; the better model is named in the UI and refit on the available history. Predictions are constrained to nonnegative demand and a cap of 1.5 times observed peak. Test error is an observed backtest metric, not a calibrated confidence interval or a validated accuracy guarantee.

Forecasts use the data's clock. Simulated and historical forecasts are labeled; old telemetry does not become a prediction for the current hour. The app predicts aggregate demand and its busiest expected hour, without claiming to identify appliances or human activities. Saving ideas reference observed busy hours and overnight use. A 50 W × 8 hour example shows hypothetical savings, with essential loads explicitly excluded from switch-off advice. Moving identical usage in time alone does not save money under the flat-rate estimate.

## Away reminders

On Home, use “I'm away” for manual mode. “I'm home” stops checks and clears the real alert. The optional setup expands to:

1. Allow notifications.
2. Set the current precise location as home and confirm that the user is actually home.
3. Allow background location separately through Android permissions/settings.
4. Enable a 200 m home geofence. Google Play services is required.

Home coordinates stay in this phone's private preferences and are supplied to Android/Google Play location services for geofencing, rather than uploaded to SILIP. A fresh location fix with accuracy within 100 m is required to save home. The user can disable automatic monitoring at any time. The feature tracks this phone; other people may still be home.

On exit, WorkManager checks the existing device-usage endpoint immediately, then approximately every 15 minutes while away. No new Lambda or database migration is needed. It sends at most one real reminder per departure if the last two consecutive 15-minute readings are both post-departure, fresh within 30 minutes, and at or above the configurable threshold (default 0.30 kW). Data that includes simulation is excluded, and failures/gaps/stale readings never count as a successful detection. This is a household-use reminder, not an appliance classifier, fire detector, guaranteed immediate alarm, or proof that a load was forgotten.

Android power management, location accuracy and internet availability can delay detection and notifications. Returning home cancels checks; the worker re-checks away/device state after its network request. Geofences are restored after boot/package replacement and on app launch. Switching the registered device clears automatic home setup and away state. Android force-stop or revoked permissions can suspend monitoring until the app is reopened/re-enabled.

“Send a demo notification” always labels the notification as a demo and can preview the experience with the current synthetic household data. It does not bypass the real alert's telemetry checks.

## Validation

`./gradlew :app:testDebugUnitTest :app:lintDebug :app:assembleDebug`

Focused tests cover benchmark cost, short/sparse history, daily forecast shape, held-out model selection, duplicate/invalid samples, and the real/fresh/consecutive/post-departure conditions for alerts. Actual geofence delivery and background timing still need a physical-device departure/return trial with fresh real sensor data. The allowlisted PoC endpoint and its access restrictions remain unchanged.

## Solar adoption journey

Home's “Make room for solar” opens a separate solar journey; it does not alter Learn. It shows the recorded share of household energy in a **9 AM–4 PM local-time window**, plus daytime/other kWh and the observation dates. This is a time-of-use proxy, not measured daylight, roof suitability or PV output. Missing readings are excluded, so the view describes the available sample rather than a complete household baseline. Synthetic readings keep their simulated label.

A slider explores a stated assumption: solar supplying a chosen share of the recorded daytime demand at matching times. Avoided grid energy is daytime kWh × chosen share; the illustrative avoided energy cost uses the same selected rate as the other screens. Installation costs, batteries, export credits, fixed charges and system output are not modeled. Users need a professional site/design assessment before making a purchase decision. Existing solar requires separate generation/import/export telemetry to assess actual performance.

The local preparation checklist uses stable IDs, is self-reported, and grants no learning XP or approval status. The external guides are [Meralco Solar and Net Metering](https://www.meralco.com.ph/residential/energy-solutions/solar-and-renewables/solar-net-metering) and [Meralco Distributed Energy Resources](https://www.meralco.com.ph/residential/energy-solutions/solar-and-renewables/distributed-energy-resources), checked 13 November 2026. The app briefly explains on-site use, grid shortfalls and eligible export credits, while the linked current guidance handles program requirements.

# Deliver supported household alerts through push

Status: open  
Type: task
Priority: medium

## Objective

Define and deliver remote push notifications only for household events supported by SILIP's data and backend.

## Motivation

Users want timely household updates, but a notification must not infer appliance-level behavior from whole-home current data.

## Acceptance criteria

- [ ] Agree on event types, thresholds, recipients, and suppression rules with API/product owners before implementation.
- [ ] Confirm the event can be derived reliably from available readings and is useful to household users.
- [ ] Define a secure FCM token registration, rotation, and deletion contract tied to the signed-in household account.
- [ ] Provide per-category notification preferences and a clear opt-out.
- [ ] Avoid placing private household data in lock-screen notification text.
- [ ] Handle expired tokens, duplicate events, retries, sign-out, and token invalidation.
- [ ] Do not name an individual appliance unless the hardware and validated telemetry support that claim.

## Dependencies

Backend/API decision on supported household event types and thresholds.

## Notes

This is not the home-exit checklist feature in ticket 05. Coordinate provider choice, Lambda triggers, token storage, and event privacy with the backend team.

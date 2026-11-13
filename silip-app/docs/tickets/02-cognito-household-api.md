# Connect Cognito and the household API

Status: deferred for the single-device PoC
Type: task  
Priority: high  
Blocked by: 01-household-onboarding

## Objective

Connect the Android app to Cognito and display the authenticated household's live usage and registered device state.

## Motivation

The current PoC uses a public endpoint restricted to one demo device. Before connecting real households, add Cognito sign-in and resolve device access server-side.

## Acceptance criteria

- [ ] Use Cognito authorization-code sign-in with PKCE and the public app client.
- [ ] Call household-scoped `/api/v1/me/usage` and `/api/v1/me/device` through CloudFront.
- [ ] Resolve device access server-side; never accept a household identifier as authorization.
- [ ] Show loading, linked, unlinked, forbidden, offline, stale, and server-error states distinctly.
- [ ] Add authorization before enabling the app for real households or exposing more device IDs.

## Dependencies

For the current PoC implementation, see the mobile Lambda in `silip/api/src/silip/mobile.py` and the device-ID entry on the Home screen. That endpoint is public and allowlisted to the demo device only.

## Notes

Use this ticket before expanding beyond the PoC device or connecting real household accounts.

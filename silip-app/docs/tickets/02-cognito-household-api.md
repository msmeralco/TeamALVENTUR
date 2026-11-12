# Connect Cognito and the household API

Status: open  
Type: task  
Priority: high  
Blocked by: 01-household-onboarding

## Objective

Connect the Android app to Cognito and display the authenticated household's live usage and registered device state.

## Motivation

The My home screen currently shows a truthful not-connected state. Household readings require internet access and an authenticated household account linked by SILIP.

## Acceptance criteria

- [ ] Use Cognito authorization-code sign-in with PKCE and the public native app client; embed no client secret or AWS credential.
- [ ] Call `GET /api/v1/me/usage` and `GET /api/v1/me/device` through the CloudFront origin.
- [ ] Send `X-Silip-Authorization: Bearer <access-token>` through CloudFront as specified by [`silip/docs/auth-contract.md`](../../../silip/docs/auth-contract.md).
- [ ] Map JSON responses to the current household domain without exposing `sin_hash`.
- [ ] Show loading, connected, no-household-link (404), unauthorized (401), forbidden (403), offline, stale, and server-error states distinctly.
- [ ] Display simulated-data status whenever the API marks readings as simulated.
- [ ] Allow refreshing after recoverable failures without losing the user's current destination.

## Dependencies

Blocked by 01-household-onboarding for the agreed user-facing states.

## Notes

The existing interface and route declarations are in `app/src/main/java/com/alventur/silipapp/data/remote/HouseholdApi.kt`. Use CloudFront, not the AWS-IAM-protected Lambda Function URL.

# Define household onboarding and device-linking

Status: open  
Type: task  
Priority: high

## Objective

Specify the first-run experience for invited household accounts and the way a household becomes linked to a registered SILIP device.

## Motivation

SILIP accounts are invite-only, and the household is linked to an account server-side. Users need clear next steps when they do not yet have access or their account has no linked household/device.

## Acceptance criteria

- [ ] Document the account invitation and household provisioning steps with the dashboard/API owners.
- [ ] Distinguish account access, registered device, device connectivity, and reading availability.
- [ ] Define understandable UI states for signed out, signed in but unlinked, linked but offline, and linked with readings.
- [ ] Keep `sin_hash` and other internal household identifiers out of the app UI and requests.
- [ ] Confirm how users request access or resolve a missing household link.

## Dependencies

None. This informs the Cognito and household API implementation.

## Notes

Follow [`silip/docs/auth-contract.md`](../../../silip/docs/auth-contract.md). Household identity is resolved using the Cognito `sub`; device installation/registration remains an operator/dashboard workflow unless the product contract changes.

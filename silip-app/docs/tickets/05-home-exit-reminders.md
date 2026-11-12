# Add opt-in home-exit checklist reminders

Status: open  
Type: task  
Priority: medium

## Objective

Let a user opt into a home-exit reminder that opens an electricity-safety checklist.

## Motivation

A location-triggered checklist can help someone remember to check non-essential appliances. The current whole-home sensor does not identify a particular appliance, so the reminder must not imply that SILIP detected one.

## Acceptance criteria

- [ ] Keep the feature off until the user explicitly enables it.
- [ ] Explain the location use and reminder trigger before requesting permission.
- [ ] Request permissions in context and follow current Android background-location requirements.
- [ ] Let users set/change the home location and pause or disable reminders.
- [ ] Provide a manual checklist path when background location or notifications are unavailable.
- [ ] Use copy that asks users to check appliances; do not claim sensor-based appliance detection.
- [ ] Handle denied permissions, approximate location, geofence delays, and notification denial with clear UI states.
- [ ] Include a battery-use review for the selected location approach.

## Dependencies

None for the manual checklist. Confirm the location setup and permission rationale before enabling geofencing.

## Notes

The notification-channel scaffold is in `app/src/main/java/com/alventur/silipapp/notifications/NotificationChannels.kt`. Location permission is not requested by the current app.

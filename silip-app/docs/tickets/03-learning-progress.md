# Persist lesson completion and rewards

Status: open  
Type: task  
Priority: medium

## Objective

Give the SILIP learning path a saved completion state, XP total, and truthful streak display.

## Motivation

The learning path currently shows starter lesson cards and a zero-completed state. Progress should persist across app restarts and remain separate from live household telemetry.

## Acceptance criteria

- [ ] Give each lesson a stable ID, unit order, and completion state.
- [ ] Persist completed lessons and XP locally across app restarts.
- [ ] Define when a lesson counts as complete and when XP is awarded.
- [ ] Prevent retrying a lesson from awarding duplicate XP.
- [ ] Calculate streaks from actual completed activity dates; never display a fabricated streak.
- [ ] Keep lessons and saved learning progress available when the device is offline.
- [ ] Do not sync household usage or learning history to an account without an explicit product/privacy decision.

## Dependencies

None for local progress. Ticket 04 should use this progress contract.

## Notes

Start with the starter catalog in `app/src/main/java/com/alventur/silipapp/education/LessonCatalog.kt` and the path UI in `app/src/main/java/com/alventur/silipapp/ui/SilipApp.kt`.

# Build multi-step lessons and practice

Status: open  
Type: task  
Priority: medium  
Blocked by: 03-learning-progress

## Objective

Expand the starter content into short lessons and interactive electricity-safety practice flows.

## Motivation

The current practice screen demonstrates progress, answer selection, submitted-answer feedback, and retry with one question. SILIP needs a reusable flow and reviewed learning content to support its Duolingo-inspired learning path.

## Acceptance criteria

- [ ] Lessons support concise explanatory steps followed by a knowledge check.
- [ ] Practice activities show step progress and accept one answer at a time.
- [ ] Show correctness and explanation only after the learner submits an answer.
- [ ] Support continue, retry, and completed states.
- [ ] Update persisted path progress and XP according to ticket 03.
- [ ] Feedback remains understandable without color and is accessible to TalkBack.
- [ ] Review user-facing electrical-safety claims before release.
- [ ] Do not claim the current whole-home sensor identifies a specific appliance.

## Dependencies

Blocked by 03-learning-progress for completion and reward behavior.

## Notes

Reuse the Compose card, progress, and answer-selection patterns established in `ui/SilipComponents.kt`.

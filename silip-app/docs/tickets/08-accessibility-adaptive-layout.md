# Review accessibility and adaptive layouts

Status: open  
Type: task  
Priority: medium

## Objective

Review the Home, Learn, Practice, and My home screens for accessibility, dark-theme contrast, and adaptive layouts.

## Motivation

The first UI pass adopts ABaKaDa's phone-first Compose patterns. SILIP should remain usable with TalkBack, larger text, and expanded/windowed Android layouts.

## Acceptance criteria

- [ ] Interactive controls have descriptive semantics and touch targets of at least 48 dp.
- [ ] TalkBack announces section headings, household status, selected answers, and submitted feedback clearly.
- [ ] Text wraps without clipping at supported font scales.
- [ ] Home tiles and lesson cards remain readable on narrow and expanded layouts.
- [ ] Light and dark themes retain readable contrast and non-color status cues.
- [ ] Content scrolls without overlapping system bars or bottom navigation.
- [ ] Review reduced-motion behavior if animations are introduced.

## Dependencies

Can begin against the current UI foundation; repeat after major flows and mascot assets are integrated.

## Notes

The current design tokens and accessibility direction are documented in `docs/ui-foundation.md`.

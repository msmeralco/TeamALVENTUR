# Integrate SILIP mascot artwork

Status: resolved  
Type: task  
Priority: low  

## Objective

Create and integrate Ali the Alitaptap artwork across SILIP's guidance and answer-feedback surfaces.

## Motivation

The app uses section-specific mascot poses to guide users through household energy information and learning.

## Acceptance criteria

- [x] Add transparent navy firefly poses for welcome, learning, practice, household checking, success, and caution.
- [x] Use different poses in each top-level section and answer-feedback state.
- [x] Keep decorative mascot art out of the TalkBack focus order.
- [x] Do not copy ABaKaDa mascot assets, name, or branding.

## Dependencies

See `docs/mascot-guide.md` for color semantics, pose mapping, and asset use.

## Notes

The assets are in `app/src/main/res/drawable-nodpi/`, mapped by `AliPose` and displayed by `PageHeader` and answer-feedback cards.

# Ali the Alitaptap

Ali is SILIP's friendly guide for household-energy learning and status explanations. The firefly has a midnight-navy body, expressive eyes, translucent navy wings, and a lightbulb-shaped abdomen.

## Color meaning

- **Emerald green bulb:** welcome, learning, linked/normal household guidance, and successful answers.
- **Vibrant orange bulb:** an unavailable or unlinked household state, caution, or a review-needed answer. Keep the tone calm; orange is not a claim that the sensor detected a specific appliance or emergency.

The abdomen color is a visual state cue. Visible copy must explain the same state so meaning never depends on color alone.

## Pose mapping

| Pose resource | Use |
| --- | --- |
| `ali_welcome.png` | Home section greeting |
| `ali_learning.png` | Learn path and lesson guidance |
| `ali_practice.png` | Practice question guidance |
| `ali_household_check.png` | Linked household status and readings explanation |
| `ali_success.png` | Correct practice answer |
| `ali_caution.png` | Unlinked household state, incorrect answer, or caution guidance |

## Composition

The shared `AliSectionHeader` follows the ABaKaDa mascot-guide pattern: a short section label and heading, then a colored panel with Ali beside a speech bubble. The same artwork can also appear inside feedback cards. Keep Ali decorative to TalkBack when nearby text conveys the guidance; do not put essential status information only in the picture.

## Android assets

Transparent PNG assets are in `app/src/main/res/drawable-nodpi/`. `AliPose` maps the six resource names, and `AliMascotIllustration` renders the selected pose. Add or replace a pose by updating those two pieces together and this pose table.

# Ali the Alitaptap

Ali is SILIP's guide for household-energy learning and status explanations. The firefly has a navy body, expressive eyes, translucent wings, and a lightbulb-shaped abdomen.

## Color meaning

- **Emerald green bulb:** welcome, learning, normal guidance, and correct answers.
- **Vibrant orange bulb:** caution, an unavailable household state, or a review-needed answer. Orange is not a claim that the sensor detected an appliance or emergency.

Visible copy must explain the same state so meaning never depends on color alone.

## Pose mapping

| Pose resource | Use |
| --- | --- |
| `ali_welcome.png` | Home greeting in the demo household |
| `ali_learning.png` | Short lesson and learning-path guidance |
| `ali_practice.png` | Daily practice question |
| `ali_household_check.png` | Bill and household-usage explanation |
| `ali_success.png` | Rewards and community guidance; correct practice answers |
| `ali_caution.png` | Caution or incorrect-answer feedback |

## Composition and accessibility

The shared `PageHeader` places a section label, title, and short explanation beside Ali. Other cards use a smaller pose when it adds guidance. Keep Ali decorative to TalkBack when nearby text carries the message; do not put essential status information only in the artwork.

## Android assets

Transparent PNG assets are in `app/src/main/res/drawable-nodpi/`. `AliPose` maps the six resource names, and `AliMascotIllustration` renders the selected pose. Add or replace a pose by updating those two pieces together and this pose table.

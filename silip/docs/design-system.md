# SILIP design system

One page for anyone building SILIP screens, slides or the demo. Tokens live in `web/src/shared/styles/tokens.css`. Rules for copy and review live in the `unslop` skill. Laws named below come from the `uiux-laws` skill.

## 1. Principles

1. **Lead with what needs action.** An engineer opens the risk map to find the one transformer that needs a crew. Everything else stays quiet. (Von Restorff, Selective Attention)
2. **Green means fine.** Green is the brand, and a healthy grid is the normal state. Orange is the only color that asks for action.
3. **Say it in words too.** Status is always color plus a word: OK, Watch, Critical. Risk always sits beside coverage and confidence.
4. **Honest data.** Simulated data carries a visible "Simulated data" label. Numbers have units and a source, or say estimate or [VERIFY].
5. **Works on a phone in a brownout.** It must work at 400px wide, with large touch targets, on a slow connection. (Fitts, Doherty Threshold)

## 2. Logo

The logo is the eye: a navy upper lid, a green lower lid and a green iris. Inside the iris are a pole, a transformer and two houses. It reads as "looking at the transformer that feeds your street." *Silip* is Filipino for "peek."

| Asset | Path | Use |
|---|---|---|
| Mark, 512px | `web/public/brand/silip-mark-512.png` | Slides, README, sign-in page |
| Mark, 128px | `web/public/brand/silip-mark-128.png` | App header (shown at 32px) |
| Favicon, 64px | `web/public/favicon.png` | Browser tab. Mark on a cream tile, so it reads on dark tabs too. |
| Touch icon, 180px | `web/public/apple-touch-icon.png` | Home screen. Mark on cream, since iOS fills transparency with black. |

- **Lockup.** Mark on the left, then the word `silip` in lowercase Space Grotesk 700, colored `--foreground`. The wordmark is live text, not an image, so it follows the theme.
- **Clear space.** Leave half the mark's height around the lockup.
- **Dark surfaces.** The navy lid is 1.07:1 on `#262626`, so in dark mode the mark sits on a cream tile (`--logo-tile`). Never recolor the lid instead.
- **Minimum size.** 24px tall. Below that, the pole and houses blur, so use the favicon.
- **Do not** recolor the mark, add a shadow or outline, put it on a busy photo, or stretch it.
- **Logo colors stay in the logo.** Navy `#022142` and green `#01A251` belong to the mark only. They are too loud for interface surfaces, and the UI uses the palette below.
- **Alternate lockup.** The arc version with the uppercase SILIP wordmark is for print and merch only. Do not use both lockups on one screen.

## 3. Color

### Palette

| Name | Hex | Role |
|---|---|---|
| Charcoal | `#262626` | Text in light mode. Cards in dark mode. |
| Sage | `#C3D2C5` | Selected item fill. Primary button in dark mode. |
| Cream | `#F2EFE3` | Page background in light mode. Text in dark mode. |
| Fern | `#58815F` | Brand: focus ring, chart lines, icons. Not for text under 18px. |
| Forest | `#254E21` | Primary button. The OK status. |

### Tokens

Every text pair below passes WCAG AA (4.5:1), measured with the WCAG 2.x formula. Light is the default theme.

| Token | Light | Dark | Use | Contrast (light / dark) |
|---|---|---|---|---|
| `--background` | `#F2EFE3` | `#1B1C1B` | Page | |
| `--card` | `#FBFAF6` | `#262626` | Cards, header, popovers | |
| `--foreground` | `#262626` | `#F2EFE3` | Body text | 14.5 / 13.1 on card |
| `--muted-foreground` | `#5E5B51` | `#ADAA9E` | Secondary text, ledes | 6.5 / 6.5 on card |
| `--secondary`, `--muted`, `--accent` | `#E7E3D4` | `#323331` | Hover fill, skeleton, neutral chip | |
| `--border`, `--input` | `#D6D0BC` | `#3D3E3B` | Hairlines | |
| `--primary` | `#254E21` | `#C3D2C5` | Primary button, link | 9.2 / 10.9 with its foreground |
| `--brand`, `--ring` | `#58815F` | `#8DB394` | Focus ring, chart series, icons | 4.3 / 6.5 on card (3:1 needed) |
| `--selected` | `#C3D2C5` | `#33433A` | Current nav item, chosen row | 9.6 / 9.1 with text |
| `--ok` on `--ok-soft` | `#254E21` on `#DCE6DC` | `#A9C9AF` on `#24322A` | OK badge | 7.5 / 7.5 |
| `--watch` on `--watch-soft` | `#7A5C00` on `#F3EBCF` | `#DDB955` on `#332B17` | Watch badge | 5.2 / 7.4 |
| `--critical` on `--critical-soft` | `#B5461A` on `#FBECE4` | `#EE8656` on `#3A241A` | Critical badge, the one action | 4.7 / 5.7 |

### Rules

- **One action color.** `--critical` marks only what needs someone to act: a Critical transformer, a destructive confirm. If two things on a screen are orange, one of them is wrong. (Von Restorff)
- **Green never warns.** Primary buttons and OK share forest green on purpose: both mean "go ahead." A warning in green would break that.
- **Do not rely on hue alone.** Orange and green look alike to people with red-green color blindness. Every status therefore carries its word, and map markers also change in size.
- **No raw colors in components.** Use tokens through Tailwind (`bg-card`, `text-critical`). Only `tokens.css` holds hex values.
- **No** gradients, glass, glows, decorative shadows, accent bars or colored edge lines. Separate things with hairlines, space and type size. The one allowed shadow is `shadow-lg` on controls that float over the map, where it shows the control sits above the map.

## 4. Type

| Role | Font | Size / line height | Tailwind |
|---|---|---|---|
| Page title | Space Grotesk 700 | 32 / 1.15 | `text-3xl` |
| Section title, card title | Space Grotesk 700 | 20 / 1.3 | `text-xl` |
| Body | Inter 400 or 500 | 16 / 1.5 | `text-base` |
| Label, meta, table cell, badge | Inter 500 or 600 | 13 / 1.4 | `text-sm` (`text-xs` is the same size) |

- Four sizes only. To emphasize, use weight or color, not a fifth size.
- Numbers in tables and readings use `tabular-nums` so columns line up.
- Sentence case everywhere except the status words OK, Watch and Critical.

## 5. Space, shape and layout

- **Spacing.** Tailwind's 4px steps. Use 8 or 12 inside a component, 16 or 24 between components, and 40 between page sections.
- **Radius.** `--radius` is 16px for cards. Buttons and inputs use `rounded-md` (10px). Chips, badges and nav pills use `rounded-full`.
- **Page.** Centered column, `max-w-6xl`, 16px gutters on mobile and 24px from `sm`. The risk map is the one full-bleed page.
- **Header.** 64px tall, `bg-card` with a bottom hairline, sticky. Lockup on the left, nav next, account menu on the right. (Jakob's Law)
- **Grouping.** Related items share a card. Unrelated items get space, not a divider. (Proximity, Common Region)

## 6. Components

All shared parts live in `web/src/shared/ui/`. Build from these before writing new ones.

| Component | What it is for |
|---|---|
| `Button` | `default` (forest) for the one main action on a screen. `outline` or `ghost` for the rest. `destructive` only inside a confirm dialog. |
| `TierBadge` | Dot plus word for OK, Watch or Critical. The only way to show tier. |
| `SimulatedLabel` | Required wherever `is_simulated` is true. |
| `PageHead` | Page title, a one-line lede and an optional row of labels. |
| `QueryView` | Loading skeleton, offline message, error with "Try again" and empty state for every data view. |
| `StateCard` | Centered message for sign-in, no access and not found. |
| `Card`, `Table`, `Tooltip`, `DropdownMenu`, `AlertDialog`, `Sonner` | shadcn/ui parts, restyled only through tokens. |
| `Map` | MapLibre on OpenFreeMap tiles. Lazy-loaded, attribution always visible. |

Interaction rules:

- **One primary button per screen.** (Hick's Law)
- **Touch targets of at least 44px** on coarse pointers, including map controls. (Fitts's Law)
- **Feedback within 400ms.** Show a skeleton shaped like the loaded page, so nothing jumps. (Doherty Threshold)
- **Focus.** Every interactive element shows a 2px `--ring` outline on keyboard focus.
- **Motion.** 150ms color transitions only. Nothing moves when `prefers-reduced-motion` is set.

## 7. Writing

From `unslop`: plain and specific, under 25 words a sentence, no em dashes, no hype words. Name things the way a Meralco engineer or a household would. Error messages say what happened and what to do next.

## 8. Before you call a screen done

- [ ] Uses tokens only, with no raw hex in components.
- [ ] Only the thing that needs action is orange.
- [ ] Status shows color plus word. Risk shows coverage and confidence.
- [ ] "Simulated data" is visible where the data is simulated.
- [ ] Has loading, empty and error states.
- [ ] Works at 400px wide with no sideways scroll.
- [ ] Checked in light and dark mode.
- [ ] Reviewed by the `design-reviewer` agent.

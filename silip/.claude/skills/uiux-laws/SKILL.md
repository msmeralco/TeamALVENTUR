---
name: laws-of-ux
description: Apply the Laws of UX (30 psychology-based design principles catalogued by Jon Yablonski at lawsofux.com) when designing, building, reviewing, or critiquing any user interface. Use this skill whenever the user builds a UI, landing page, app screen, form, dashboard, onboarding flow, navigation, or component; asks for a UX review, heuristic audit, or usability feedback; asks why a design feels confusing, slow, or cluttered; or mentions Hick's Law, Fitts's Law, Jakob's Law, Miller's Law, Gestalt principles, cognitive load, or any other named UX law, even if they never say "Laws of UX".
---

# Laws of UX

A working reference for 30 UX principles grounded in psychology. Use it in two modes:

1. **Build mode**: when creating UI, quietly apply the relevant laws while designing. Do not lecture the user about them unless asked.
2. **Review mode**: when auditing a design, screenshot, or code, walk the checklist below and report findings tied to named laws, each with a concrete fix.

Full detail for every law (definition, origin, takeaways, misuse warnings) lives in `references/laws.md`. Read the relevant entries before a deep review.

## The 30 laws at a glance

Grouped by the question each one answers.

### Is it easy to decide and act?
- **Hick's Law**: decision time grows with the number and complexity of choices.
- **Choice Overload**: too many options overwhelm and stall people.
- **Fitts's Law**: time to hit a target depends on its size and distance.
- **Doherty Threshold**: keep system response under about 400ms so neither side waits.
- **Paradox of the Active User**: people skip instructions and start using things right away.

### Can people hold it in their heads?
- **Cognitive Load**: the mental effort needed to understand and use an interface.
- **Working Memory**: the small, temporary store people use to complete tasks.
- **Miller's Law**: working memory holds roughly 7 plus or minus 2 items.
- **Chunking**: grouping information into meaningful units makes it easier to process.
- **Selective Attention**: people focus on stimuli tied to their goals and filter out the rest.
- **Cognitive Bias**: systematic thinking errors shape perception and decisions.

### Does it match what people expect?
- **Jakob's Law**: users spend most of their time elsewhere and expect your product to behave like the ones they know.
- **Mental Model**: people act on a simplified internal picture of how a system works.
- **Postel's Law**: accept varied input generously, output predictably and strictly.
- **Tesler's Law**: every system has irreducible complexity; decide who absorbs it.
- **Occam's Razor**: among equally good options, prefer the one with fewest assumptions and elements.

### Is the visual structure clear? (Gestalt)
- **Law of Proximity**: nearby things read as a group.
- **Law of Common Region**: things inside a shared boundary read as a group.
- **Law of Similarity**: things that look alike read as related.
- **Law of Uniform Connectedness**: visually connected things read as more related.
- **Law of Prägnanz**: people interpret complex visuals in the simplest possible form.

### What do people notice and remember?
- **Von Restorff Effect**: the item that differs from its neighbors is remembered.
- **Serial Position Effect**: first and last items in a series are remembered best.
- **Peak-End Rule**: experiences are judged by their most intense moment and their ending.
- **Zeigarnik Effect**: unfinished tasks stay in memory more than finished ones.
- **Aesthetic-Usability Effect**: attractive designs are perceived as easier to use.

### What keeps people moving?
- **Goal-Gradient Effect**: motivation rises as people get closer to a goal.
- **Flow**: full, energized immersion when challenge matches skill.
- **Parkinson's Law**: tasks expand to fill the time available.
- **Pareto Principle**: roughly 80% of effects come from 20% of causes.

## Review checklist

Run through these when auditing. Report only what actually applies.

1. **Choices**: Count primary actions per screen. More than one competing primary CTA, or long unfiltered option lists? (Hick, Choice Overload)
2. **Targets**: Are key buttons large, close to where attention already is, and at least ~44px on touch? Are destructive actions far from common ones? (Fitts)
3. **Speed**: Any interaction that takes over 400ms without feedback? Add skeletons, optimistic UI, or progress. (Doherty)
4. **Memory**: Does the user have to remember something from a previous screen? Are lists, nav items, or form fields unchunked? (Working Memory, Miller, Chunking, Cognitive Load)
5. **Conventions**: Does anything (nav placement, icons, cart, search, link styling) deviate from patterns users know without a strong reason? (Jakob, Mental Model)
6. **Input tolerance**: Do forms reject reasonable formats (phone with spaces, dates, casing)? (Postel)
7. **Complexity placement**: Is complexity pushed onto the user that the system could handle (defaults, autofill, inference)? (Tesler)
8. **Grouping**: Does spacing, containment, color, and connection match the actual logical relationships? (Proximity, Common Region, Similarity, Uniform Connectedness, Prägnanz)
9. **Emphasis**: Is exactly the right thing visually distinct? Is emphasis diluted by overuse? (Von Restorff, Selective Attention)
10. **Order**: Are the most important items first or last in lists and nav? (Serial Position)
11. **Moments**: Is the peak moment delightful and the ending (confirmation, success, exit) strong? Are error peaks softened? (Peak-End)
12. **Progress**: Do multi-step flows show progress and give a head start? Are incomplete tasks surfaced to invite return? (Goal-Gradient, Zeigarnik)
13. **Learnability**: Can someone succeed without reading help text? Is guidance in context rather than up front? (Paradox of the Active User)
14. **Polish**: Is visual quality hiding usability problems in testing? (Aesthetic-Usability)
15. **Focus**: Does effort go to the 20% of features most people use? (Pareto)
16. **Bloat**: Can any element be removed without loss? (Occam's Razor)

## Output format for reviews

For each finding:

```
**[Law name]** – Issue: <what is wrong, where>
Fix: <specific change>
Priority: High / Medium / Low
```

Lead with the highest-impact issues. Close with 2 to 3 things the design already does well, named by law.

## Guardrails

- Laws are heuristics, not rules. Note tradeoffs when two laws pull against each other (for example Hick vs. discoverability, Jakob vs. differentiation, Aesthetic-Usability vs. honest testing).
- Do not misuse persuasion-adjacent laws (Cognitive Bias, Zeigarnik, Goal-Gradient, Peak-End) to build dark patterns: fake urgency, guilt-driven re-engagement, or hiding unsubscribe.
- Miller's 7±2 is about working memory, not a hard cap on menu items. Do not cite it to arbitrarily truncate navigation.
- Prefer evidence from real user testing over citing a law when the two disagree.

## Source

Based on Laws of UX by Jon Yablonski (https://lawsofux.com), licensed CC BY-NC-ND 4.0. Summaries here are original paraphrases for internal, non-commercial use. See the site and the book *Laws of UX* (O'Reilly) for the canonical text.

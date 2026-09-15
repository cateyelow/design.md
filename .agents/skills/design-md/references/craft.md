# Craft: what to look at in the rendered page

Read while designing in HTML (step 6) and during the craft pass (step 7). The audit catches known tells; this is what only looking at the page catches.

## The structural idea

Write it in one sentence before any markup, from `direction.world` and `direction.layout`: "a technical data sheet with a fixed clause index and marginal notes", "a single long table where each row is one service", "a photo essay whose captions carry the argument". Then check the render against it:

- Could the sections be reordered without loss? Then the idea is not in the layout yet.
- Does the first screen do the idea's job, or is it a headline block that could sit on any page?
- Is there one element on the page that only this business could have (its hours, its price list, its own photo, its actual document)?

The default that arrives when there is no idea: full-width centered headline, subtitle, two buttons, a picture on the right, then three cards, then a table, then a form. If the render looks like that, the idea lost.

## Type

- Korean measure 35 to 45 characters, Latin 60 to 75. A 900px line of 17px Hangul is not a designed column.
- A headline is not one size bigger than everything: give one place real scale and keep the rest near the text size. A page where the only typographic move is a huge bold headline reads as generated, even in a licensed Korean face.
- Set `font-variant-numeric: tabular-nums` wherever numbers stack, and align decimals in tables.
- Check the last line of every headline at 390px for one orphaned syllable; fix with explicit `<span>` phrase units or a different break, not by shrinking the type.
- `word-break: keep-all` for Korean, and check that no word breaks mid-syllable.
- Hang quotation marks, bullets and clause numbers into the margin instead of indenting the text after them.
- One family for running text. A second family earns its place only as display or as figures.

## Space and rhythm

- One spacing scale, used everywhere; no one-off values.
- Rhythm should change with content: a dense table needs less air than a statement. Identical padding on every section is what makes a page feel like a template.
- Put deliberate emptiness in one place and deliberate density in another. Evenly comfortable everywhere is the average look.
- Align to a few strong vertical lines. If every element starts at the same left edge and ends at the same right edge, the grid is doing nothing.

## Where the world shows up

Ornament comes from `direction.world`, not from a component library: a document number and revision row, a crop mark, a form field rule, a stamped page number, a catalogue code beside each item, a ruler tick edge. One or two such devices, used consistently, carry more than a decorative accent on every block.

Refuse by default: pill badges above the headline, three equal icon cards, rounded card grids, gradient text, glassy panels, glows, a violet accent, an arrow glyph in every button, a circular seal drawn in CSS, fade-up-on-scroll everywhere, emoji as icons, a dark terminal block used as decoration.

## Detail that shows a person was there

- Captions with figure numbers, units in table headers, footnotes for the source of a number.
- Hover, focus-visible, active and disabled states for everything clickable; focus rings that fit the design.
- Images cropped per breakpoint, with the subject off center, and the same light direction across the set.
- `prefers-reduced-motion` honoured, and motion only where it explains something.
- Real text in the first screen: no placeholder proportions that assume copy which does not exist yet.

## Looking at it

Screenshot both widths every round (`scripts/shot.py`, which also writes readable crops) and look at the crops, not the whole scaled-down page. Between rounds, ask: what would a reader notice first, and is that what should be noticed? Then fix the single worst thing, and shoot again. Stop when the page holds up at both widths and nothing in the render contradicts DESIGN.md.

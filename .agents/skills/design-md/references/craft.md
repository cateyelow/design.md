# Craft: what to look at in the rendered page

Read while designing in HTML (step 6) and during the craft pass (step 7). The audit catches known tells; this is what only looking at the page catches.

Two different things live here and must not be mixed. The execution floor applies to every page, whatever it looks like. The look belongs to the direction: the world, the sourced colors and the layout archetype decide it, not a house style of the model. A rule like "hang the clause numbers and add a figure caption" is not craft; it is one look, and applied everywhere it becomes the look of generated pages.

## The structural idea

Write it in one sentence before any markup, from `direction.world` and `direction.layout`: "a supermarket flyer where every item is a price tag", "a bathhouse price board with one row per service", "a weather forecast graphic that maps the week". Then check the render against it:

- Could the sections be reordered without loss? Then the idea is not in the layout yet.
- Does the first screen do the idea's job, or is it a headline block that could sit on any page?
- Is there one element on the page that only this business could have (its hours, its price list, its own photo, its actual document)?

There are two defaults that arrive when there is no idea. The first generation: full-width centered headline, subtitle, two buttons, a picture on the right, three cards, a table, a form. The second, which arrives when a model tries to look designed: see "The second generated look" below. If the render looks like either, the idea lost.

## The second generated look

Asked to avoid the purple-gradient template, models converge on a tasteful editorial page instead, and they do it on every project regardless of the direction labels. Measured on two pages built for different directions in this skill's own pilot, the grounds were `#f2f1ec` and `#f3efe6`, the inks `#15150f` and `#3a3833`, and the accents a single red or orange. Its parts:

- a tinted off-white paper ground and a warm near-black ink, with at most one rust, red, orange or ochre accent;
- hairline rules as the main structure: rules under every heading, between every row, around every cell;
- small letter-spaced labels, often uppercase or in monospace ("SPEC 01", "FIG. 2", document codes);
- numbered section headings and hanging clause numbers;
- figure captions, footnote marks and revision tables used as decoration rather than because the content has sources and figures;
- a document or specification-sheet metaphor with a fixed index column.

Each part is good typography somewhere. Together, by default, they are a signature. `audit.py` reports it as `generated-look` (`paper-ink-accent`) and compares every page with the ledger's recent fingerprints (`near-recent`), so two projects cannot quietly share it. Do not answer the warning by swapping `#f2f1ec` for `#f4f1ea`: change where the values come from and which habits the world actually has.

## Color comes from a source

Never type a hex value from taste. Take colors from the material (`palette.py extract` on the business's photos), from a published color dictionary (`palette.py wada`), or from the brand guide, and let `palette.py roles` fix contrast by moving lightness only. Record the source in `direction.colorSource`. Then use color the way the source uses it: a Wada combination is three colors in comparable areas, not two neutrals and a dot; a storefront's green awning is a large surface, not a link color. A page whose chromatic area is under a few percent is a neutral page, whatever its accent is.

## Type

- Korean measure 35 to 45 characters, Latin 60 to 75. A 900px line of 17px Hangul is not a designed column.
- Decide the scale from the world. A broadcast caption, a poster or a flyer wants very large type in one place; a form, a price board or a manual wants sizes close together. The tell is the same moderate ratio on every project (the fingerprint records it as `scale`).
- Set `font-variant-numeric: tabular-nums` wherever numbers stack, and align decimals in tables.
- Check the last line of every headline at 390px for one orphaned syllable; fix with explicit `<span>` phrase units or a different break, not by shrinking the type.
- `word-break: keep-all` for Korean, and check that no word breaks mid-syllable.
- One family for running text. A second family earns its place only as display or as figures. Monospace is for code, and for figures when the world really prints them that way (a receipt, a ticket machine, a terminal); it is not a label style.

## Space and rhythm

- One spacing scale, used everywhere; no one-off values.
- Rhythm should change with content: a dense table needs less air than a statement. Identical padding on every section is what makes a page feel like a template.
- Put deliberate emptiness in one place and deliberate density in another. Evenly comfortable everywhere is the average look.
- Align to a few strong vertical lines. If every element starts at the same left edge and ends at the same right edge, the grid is doing nothing.

## Where the world shows up

Ornament comes from `direction.world`, and different worlds have different ornaments. A home shopping caption has a saturated price bar, a countdown and a phone number set huge. A pharmacy envelope has a form grid, a dosage table and one clinical green. A snack bag back has a nutrition table, a barcode and a mascot. A subway sign has pictograms, line colors and a strict type size ladder. A bathhouse price board has painted tiles, a row per service and prices larger than names. Take the one or two devices that belong to this world and use them consistently; if the devices you reached for are rules, captions and numbered headings, check whether the world really has them or whether they came from habit.

Refuse by default: pill badges above the headline, three equal icon cards, rounded card grids, gradient text, glassy panels, glows, a violet accent, an arrow glyph in every button, a circular seal drawn in CSS, fade-up-on-scroll everywhere, emoji as icons, a dark terminal block used as decoration, a small icon in its own square beside every heading, a grid of colored boxes with one topic each as the whole page structure, and the second generated look above.

## Detail that shows a person was there

- Units in table headers, and the source of a number next to the number when the number has one. Put what a table's numbers mean into its headers; a legend sentence is only for a table whose headers cannot carry it.
- Hover, focus-visible, active and disabled states for everything clickable; focus rings that fit the design.
- Images cropped per breakpoint, with the subject off center, and the same light direction across the set.
- `prefers-reduced-motion` honoured, and motion only where it explains something.
- Real text in the first screen: no placeholder proportions that assume copy which does not exist yet.

## Copy: each fact once

Generated copy gives itself away less by single phrases than by saying everything again. Three pages built with this skill by fresh agents showed it: a bakery gave its first bake time, 07:30, in six places (the hero sentence, the table, a "next bake" widget, a sentence under it, the day timeline, the rules list); a climbing gym gave its Saturday 11:00 trial class and its 35,000원 price in the hero, the first section, the price list, the timetable and the closing block; a tax office ended with a 표시사항 list that restated eight of the nine facts above it, after sentences telling the reader that the fees were "all in the table" and what "this page does not cover". Each block was reasonable alone. Together they are a page that talks at the reader.

- Give every fact one home: the place a reader looking for that kind of fact goes. When the page has a price list, every price is in it; when it has a timetable, every opening hour and class time is in it. A course block then keeps what only it says (length, group size, what is taught) and names the course without restating its price or hours. Without a price list, the course block holds its own price.
- An action may carry what that action needs: the phone number with the booking deadline beside the call button, the class time beside the booking button. When the first screen and the closing block offer the same action, the first screen carries the offer's facts and the closing block can be the action alone. The footer may hold the name, address, hours and phone once; when the contact block sits directly above it, the footer drops what that block just said. Nothing else repeats a fact.
- When two devices show the same data (a timetable and a day timeline, a fee table and a disclosure list), keep the one that does the job and remove the other whole. Stripping the values out of one leaves a decoration that still points at the data.
- A table or diagram keeps its headers, units and labels. Cut the sentence that repeats them, not the labels; a table needs no sentence announcing what it shows and no list restating it.
- Cut sentences about the page instead of the offer: what a table contains, what the page leaves out, which questions the reader must be asking. Material that is missing is recorded in the brief and simply absent from the page.
- The first screen says what this is and where or for whom, at most two short sentences (a letter's opening included), and the action. A paragraph summarizing the sections below is the intro every reader skips.
- `direction.tone` decides the voice, not the length. A letter is still a few sentences; the neighborhood owner still says each thing once.
- A heading followed by a sentence that says the heading again is one of the two too many.

Cut pass, after the craft pass. Read the page as plain text top to bottom (`document.body.innerText` in the browser console) at both widths, because a header hidden at 390px may be the only place a fact appears. Keep each fact in its home and strike its other appearances, even when a copy came first in reading order; strike every sentence about the page. Then repair what the cut left:

- a sentence that lost its repeat keeps what only it said as a whole sentence, never a fragment;
- a fact that lived only in a deleted block moves to the block it belongs to;
- a unit that only a legend sentence gave moves into the table header;
- a diagram that lost its explaining sentence keeps a short label naming what it measures;
- a heading that no longer fits what is under it is renamed or merged with its neighbor;
- an emptied table column is removed, and rows that became identical collapse into one ("월~금 12:00~23:00");
- the layout closes the gap without shrinking the surfaces the color strategy assigned, for example by putting the section on a grid another section already uses or by letting the remaining line take the freed type size.

Update DESIGN.md where the cut removed a component: its description, the tokens only it used, and any `direction` axis the page no longer does (a removed scroll device changes `motion`). Last, check that everything a customer needs is still on the page. The shorter page is usually the one that reads as written by the business.

## Looking at it

Screenshot both widths every round (`scripts/shot.py`, which also writes readable crops) and look at the crops, not the whole scaled-down page. Between rounds, ask: what would a reader notice first, and is that what should be noticed? Then fix the single worst thing, and shoot again. Put the screenshot next to the last two projects in the ledger: if a stranger would guess the same designer made all three, the direction did not reach the render. Stop when the page holds up at both widths and nothing in the render contradicts DESIGN.md.

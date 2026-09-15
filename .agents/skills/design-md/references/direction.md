# Choosing a direction

Read when proposing or adjusting a direction, collecting references, or writing the layout prompt.

## What each axis decides

| Axis | Decides | Why it matters |
|---|---|---|
| narrative | the role and order of sections: what persuades | The strongest convergence is the section skeleton (hero, three features, testimonials, pricing, FAQ, CTA). Removing gradients does not help while that skeleton stays. |
| world | one concrete object or medium the page belongs to | A specific reference carries many decisions and names what the page is not. "Tool company specification sheet" rules out glow, blobs and pill badges without a list. |
| layout | the archetype and reading order | Editorial grid, poster, catalog, document with fixed contents, split screen, table-first, photo essay, flyer. |
| type | a pairing id from fonts.json | Role split between display and text; the Korean display face sets the page's first impression more than any Latin accent. |
| color | how many colors and where they come from | Paper and ink with one stamp red, two colors taken from the brand photo, a riso two-color print. |
| image | the physical treatment of pictures | Film grain, black and white documentary, product cut-out with real shadow, collage, none, halftone. |
| density | the ratio of space to information | Wide margins, normal, table and list dense. |
| motion | how much moves | None, hover and focus only, one scroll-linked moment. |
| tone | who seems to be speaking | Plain manual, neighborhood owner, expert specification, letter. |

Brand-fixed choices are locked with `--lock axis=value`. The options are a curated list: add an option only after it produced a good page, remove options that keep producing weak pages, and add conflict rules when two options fight. The quality of the list is the quality of the output.

## Choosing among candidates

Start from the brief's persuasion problem, for example "first-time visitors suspect the price; within two screens they must see a real finished example and the cost structure". Prefer the candidate whose narrative answers that problem, then check that layout and image treatment can carry the real material you actually have. A photo essay without photos, or a table-first page without comparable data, is the wrong candidate even if it is novel.

The ledger rule (at least five of nine axes different from each of the last five entries, and two of narrative, layout, image) is a starting threshold. Color-only variation reads as the same site. Use one ledger for all of the user's projects so different clients stop converging.

## Reference images

References steer harder than prompts or skills, and a single reference produces a copy. For each project:

- Collect 3 to 5 references that represent different axes, and write what to take from each: "A: camera height and margin placement only", "B: type density only", "C: the distance to the subject in photos only".
- Look beyond web galleries: books, exhibition catalogs, packaging, industry documents, signage, product manuals. [Minimal Gallery](https://minimal.gallery/) and [Awwwards](https://www.awwwards.com/) are useful for web craft, but their top pages are what everyone copies.
- A search like "pro desktop app UI" on Pinterest suits productivity tools. Desktop tool screens optimize repeated work; a landing page has to persuade a first visitor, so borrow density and hierarchy, not the structure.
- The final reference for implementation is the project's own comp (step 6), not the gallery images.

## getdesign.md and brand DESIGN.md files

[getdesign.md](https://getdesign.md/) collects DESIGN.md analyses of 550+ sites. Picking Vercel, Apple, Airbnb, Figma or Linear gives quick coherence, which is why everyone picks them and pages converge; applying a recognizable brand's look to another business can also read as imitation of that brand. Use these files to learn how tokens and rules are organized and how spacing rhythm or hierarchy is reasoned, then take the look from this project's direction. Do not copy another brand's colors, typefaces, signature graphics or wording.

## Prompting the layout

Do not ask the model for "the best layout for this purpose": that returns the most common answer. Give it the brief's persuasion problem, the chosen narrative and layout archetype, the real material list, and the comp. Ask it to explain which section answers which doubt. During implementation, targeted checks keep it from drifting: "are padding and widths consistent with the spacing scale", "is any motion awkward or unrequested", "does the type hierarchy follow DESIGN.md". Frame review as differences from the comp and DESIGN.md, not as taste.

Repeated polishing can erase intended character: wide margins and asymmetry get "balanced" back to the average. Write the reason for such choices in DESIGN.md so reviewers treat them as decisions.

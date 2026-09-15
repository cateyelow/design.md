---
name: design-md
description: Build or redesign a landing page or marketing site that should read as designed by a person, and read, create or update a project's DESIGN.md. Chooses a per-project art direction against a ledger, typesets with verified commercial-use fonts, generates imagery with Codex image generation, and audits the rendered page for AI-generated design tells.
---

# Landing pages that do not look generated

Outcome: a working page whose direction was chosen for this business, recorded in DESIGN.md, built from real material, typeset with licensed font files, and checked in a real browser at desktop and mobile widths.

Generated pages look alike because the model takes the most average option at every decision: the centered hero with a pill badge, three icon cards, one sans family, a violet gradient, stock marketing copy. Told to avoid that, it lands on a second default instead: off-white paper, warm black ink, one rust accent, hairline rules, small letter-spaced labels and numbered headings, on every project, whatever the direction labels say. Designer-made polish skills raise quality but also pull every page toward the same finish. This skill takes the values from outside the model (the business's photos, a published color dictionary, the brand), measures what the browser actually drew, and compares it with recent projects, while keeping a fixed quality floor.

A small UI fix does not need this workflow. Preserve the existing DESIGN.md, tokens and components, make the change, and verify it.

## 1. Brief and real material

Read an existing DESIGN.md, brand assets, tokens, component library and current screens first. Approved brand choices (logo, colors, typefaces) stay; they become locked axes in step 2. When sources conflict, resolve the choice that matters from the conversation or ask one focused question.

Write the brief in a few lines: who arrives, what they doubt, the one action, and what they must understand in the first two screens. Collect real material: photos (a phone photo is fine), prices, hours, addresses, product screens, reviews with their source. Mark what is missing. Do not invent numbers, testimonials, client logos or people; a section without material is removed, not filled. Concrete material is the strongest defence against a generic page.

## 2. Choose a direction

```text
python scripts/direction.py propose --project "<name>" --count 3 --ledger ~/.claude/design-ledger.json [--lock color="브랜드 기존 색 그대로, 새 색 금지"]
```

Each candidate fixes nine axes: narrative, reference world, layout archetype, font pairing, color strategy, image treatment, density, motion and copy tone. Candidates are filtered against the most recent ledger entries so the new site differs in at least five axes and in two of narrative, layout and image, and its reference world comes from a different group (print, places, screens, objects) than the last two projects. Each color strategy names where its values come from; a strategy that needs photos you do not have is the wrong candidate. The draw only widens the options: choose the candidate that serves the brief and say why; redraw or adjust an axis that fights the brief. Show the candidates when the user is present and the choice is consequential. Read [references/direction.md](references/direction.md) for what each axis decides, how to use reference images and getdesign.md without cloning a brand, and how to write layout prompts.

## 3. Record the decision in DESIGN.md

Write DESIGN.md before code, following [FORMAT.md](FORMAT.md): an Overview built on the reference-world sentence and the reason, a `direction` block with all nine axes plus `reason`, `differs` and `colorSource`, tokens, the `fonts` block from step 4, and a short Do's and Don'ts specific to this direction (the tells this direction is most likely to slide into). Keep narrow amendments narrow and inspect token diffs before replacing a file.

Color tokens come from the recipe of the chosen color strategy, never from taste:

```text
python scripts/palette.py extract <photos of the business>            # or
python scripts/palette.py wada --draw 3 --project "<name>"            # then pick one combination
python scripts/palette.py roles --colors "<hex,hex,hex>" --source "<photo:... | catalog:wada#N | brand:...>" --scheme light|dark|ground
```

`roles` moves only lightness until text contrast holds and prints every move. Copy its `colors` and `direction.colorSource` into DESIGN.md. Use the colors in the areas the source uses them; three sourced colors squeezed into one link color is the neutral page again.

```text
python scripts/designmd.py lint DESIGN.md
```

This runs the landing fork of the design.md CLI and reports which CLI ran. Lint errors must be 0 (an Adobe Fonts or KoPub face set to ship on the web is an error). Act on `generic-typeface`, `ai-palette` and `direction-record` warnings, or record the reason in `direction`. `ai-palette` now also warns on the paper, ink and one warm accent palette unless `direction.colorSource` names a real source.

## 4. Fonts

Pick a pairing from [references/fonts.json](references/fonts.json); the chosen pairing id is the `type` axis. Then:

```text
python scripts/fonts.py fetch <display-id> <text-id> --dest <project>/assets/fonts --weights 400,700
python scripts/fonts.py design-block <ids> --dest <project>/assets/fonts --prefix <path used by the site>
```

`fetch` downloads from the official distribution, keeps the license text, records SHA-256 in `fonts.lock.json` and writes `fonts.css`. Never self-host files synced by Adobe Fonts or any face with `webEmbedding: false`; they may appear only rasterized inside images. Serve `modify: false` faces exactly as distributed. A user-supplied paid font needs a license that covers web embedding, recorded in `fonts`. Read [references/fonts.md](references/fonts.md) before choosing faces for a client site or adding a font to the catalog.

## 5. Images

Generate backgrounds, scenes, textures and mood with Codex image generation. Do not generate the product's exact form, real UI, the people presented as customers, staff or doctors, before/after results, or any evidence; use originals for those. Prompt first, `-i` references last, no text inside images. Name the DESIGN.md colors in the prompt: left to itself the image model picks the same muted warm grade as the page model, and the photos pull the page back to it. Read [references/imagery.md](references/imagery.md) for the command, prompt skeletons per image treatment, the role of each reference image, the retouching pass and the advertising and labeling limits.

## 6. Design in HTML

Design in the browser, not in a mock-up tool: the page is the design. Before writing markup, name the structural idea in one sentence ("a technical data sheet with a fixed clause index and marginal notes"). If the sections could be reordered without loss, there is no idea yet, and the page will fall back to hero, three cards, testimonials, CTA.

Build the whole page with the real fonts (`fonts.css`, or `designmd.py export --format css-fonts`), the real material and the processed images, then look at it:

```text
python -m http.server 8000 --bind 127.0.0.1        # in the site folder
python scripts/shot.py http://127.0.0.1:8000/ --widths 1440,390 --out shots
```

Look at both screenshots at full size every round, fix what is wrong, shoot again. Three or four rounds is normal. What to look for is in [references/craft.md](references/craft.md): the structural idea, type detail, the spacing scale, where the world shows up, and the default shapes to refuse.

## 7. Craft pass

The first render is the average version of the idea. Spend a round on the execution a person would bother with and a machine skips: a measure of 35 to 45 Korean characters, no orphaned syllables, tabular figures where numbers stack, one deliberate crowded place and one empty one, section rhythm that changes with the content, states for every interactive element. Keep that floor separate from the look: the ornaments come from `direction.world`, never from a component library and never from a house style. Rules under every heading, small letter-spaced labels, numbered headings and figure captions are one look, not craft. Keep the Korean copy free of em/en dashes and spaced hyphen connectors, and keep one speech level.

## 8. Verify

```text
python scripts/audit.py http://127.0.0.1:8000/ --widths 1440,390 --out <dir> --ledger ~/.claude/design-ledger.json
```

Serve the page (`python -m http.server 8000 --bind 127.0.0.1` in the site folder); `file://` blocks preloaded fonts and adds false console errors. Resolve every error (`font-fallback`, `overflow-x`). Fix each warning or justify it from DESIGN.md; a skipped check is not a pass. `generated-look` and `near-recent` are measured from the render, not from the labels: fix them by changing the color source or the habits the page leans on, not by nudging a hex value, and justify them only when the brand locks that look. Put the 1440px screenshot beside the last two ledger projects; if they read as one designer's work, the direction did not reach the page. Run the project's own checks and use the page in a real browser. For a substantial page, have the model that did not implement it review against the brief and DESIGN.md and report violations only. Designer polish skills may review spacing, type and motion, but a recorded direction choice is not a defect. Read [references/review.md](references/review.md) for the tells catalog, copy rewrites, cross-model review prompt and blind test.

## 9. Record and report

```text
python scripts/direction.py record --project "<name>" --pick direction.json --fingerprint <audit dir>/report.json --ledger ~/.claude/design-ledger.json
```

The fingerprint is what the next project is compared with, so record it from the finished page. Report the direction and why, the color source, fonts with license and verified date, which images are generated and which are original, audit counts including skipped checks, and what is still missing.

## Tool notes

- The landing fork lives at https://github.com/cateyelow/design.md (branch `landing`). `designmd.py` looks for it in `$DESIGNMD_FORK`, `~/GitHub/design.md` and `C:/GitHub/design.md`; without it the upstream CLI runs and the fonts, direction and palette rules are missing. Setup: `git clone -b landing https://github.com/cateyelow/design.md` then `bun install` in `packages/cli`.
- On Windows the `design.md` binary name collides with the Markdown file association; the scripts always call the dot-free `designmd` entry.
- `shot.py` drives installed Chrome through Playwright, waits for `document.fonts.ready` and writes one full-page PNG per width. `audit.py` writes the same screenshots; `shot.py` is the fast loop while designing.
- `fingerprint.py <url>` measures a page on its own (ground, ink, accents, type scale, decoration habits, matched generated looks). Its thresholds were checked against 14 human-made sites (no false `paper-ink-accent`; Stripe and Linear match `violet-gradient-saas`, the look models copy from them) and two generated pilots (both matched); it is a detector of known looks, not proof that a page reads as human.
- `palette.py wada` downloads Sanzo Wada's A Dictionary of Colour Combinations as digitized by mattdesl at a pinned commit with a SHA-256 check and caches it in `~/.cache/design-md`; the repository licenses its code but states no license for the data, so the file is not bundled.

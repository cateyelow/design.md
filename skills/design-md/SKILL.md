---
name: design-md
description: Build or redesign a landing page or marketing site that should read as designed by a person, and read, create or update a project's DESIGN.md. Chooses a per-project art direction against a ledger, typesets with verified commercial-use fonts shared by Photoshop comps and the web build, generates imagery with Codex image generation, and audits the rendered page for AI-generated design tells.
---

# Landing pages that do not look generated

Outcome: a working page whose direction was chosen for this business, recorded in DESIGN.md, built from real material, typeset with licensed font files, and checked in a real browser at desktop and mobile widths.

Generated pages look alike because the model takes the most average option at every decision: the centered hero with a pill badge, three icon cards, one sans family, a violet gradient, stock marketing copy. Designer-made polish skills raise quality but also pull every page toward the same finish. This skill replaces the defaults with recorded, varied choices and keeps a fixed quality floor.

A small UI fix does not need this workflow. Preserve the existing DESIGN.md, tokens and components, make the change, and verify it.

## 1. Brief and real material

Read an existing DESIGN.md, brand assets, tokens, component library and current screens first. Approved brand choices (logo, colors, typefaces) stay; they become locked axes in step 2. When sources conflict, resolve the choice that matters from the conversation or ask one focused question.

Write the brief in a few lines: who arrives, what they doubt, the one action, and what they must understand in the first two screens. Collect real material: photos (a phone photo is fine), prices, hours, addresses, product screens, reviews with their source. Mark what is missing. Do not invent numbers, testimonials, client logos or people; a section without material is removed, not filled. Concrete material is the strongest defence against a generic page.

## 2. Choose a direction

```text
python scripts/direction.py propose --project "<name>" --count 3 --ledger ~/.claude/design-ledger.json [--lock color="브랜드 기존 색 그대로, 새 색 금지"]
```

Each candidate fixes nine axes: narrative, reference world, layout archetype, font pairing, color strategy, image treatment, density, motion and copy tone. Candidates are filtered against the most recent ledger entries so the new site differs in at least five axes and in two of narrative, layout and image. The draw only widens the options: choose the candidate that serves the brief and say why; redraw or adjust an axis that fights the brief. Show the candidates when the user is present and the choice is consequential. Read [references/direction.md](references/direction.md) for what each axis decides, how to use reference images and getdesign.md without cloning a brand, and how to write layout prompts.

## 3. Record the decision in DESIGN.md

Write DESIGN.md before code, following [FORMAT.md](FORMAT.md): an Overview built on the reference-world sentence and the reason, a `direction` block with all nine axes plus `reason` and `differs`, tokens, the `fonts` block from step 4, and a short Do's and Don'ts specific to this direction (the tells this direction is most likely to slide into). Keep narrow amendments narrow and inspect token diffs before replacing a file.

```text
python scripts/designmd.py lint DESIGN.md
```

This runs the landing fork of the design.md CLI and reports which CLI ran. Lint errors must be 0 (an Adobe Fonts or KoPub face set to ship on the web is an error). Act on `generic-typeface`, `ai-palette` and `direction-record` warnings, or record the reason in `direction`.

## 4. Fonts: the same files in Photoshop and on the web

Pick a pairing from [references/fonts.json](references/fonts.json); the chosen pairing id is the `type` axis. Then:

```text
python scripts/fonts.py fetch <display-id> <text-id> --dest <project>/assets/fonts --weights 400,700
python scripts/fonts.py install <ids> --dest <project>/assets/fonts        # for Photoshop
python scripts/fonts.py ps-names <ids> --dest <project>/assets/fonts       # PostScript names for the comp
python scripts/fonts.py design-block <ids> --dest <project>/assets/fonts --prefix <path used by the site>
```

`fetch` downloads from the official distribution, keeps the license text, records SHA-256 in `fonts.lock.json` and writes `fonts.css`. Never self-host files synced by Adobe Fonts or any face with `webEmbedding: false`; they may appear only rasterized inside images. Serve `modify: false` faces exactly as distributed. A user-supplied paid font needs a license that covers web embedding, recorded in `fonts`. Read [references/fonts.md](references/fonts.md) before choosing faces for a client site, adding a font to the catalog, or converting Photoshop type settings to CSS.

## 5. Images

Generate backgrounds, scenes, textures and mood with Codex image generation. Do not generate the product's exact form, real UI, the people presented as customers, staff or doctors, before/after results, or any evidence; use originals for those. Prompt first, `-i` references last, no text inside images. Read [references/imagery.md](references/imagery.md) for the command, prompt skeletons per image treatment, the role of each reference image, the Photoshop post-processing pass and the advertising and labeling limits.

## 6. Comp before code

Build a desktop (1440 wide) and a mobile (390 wide) comp with the real fonts and processed images:

```text
python scripts/photoshop_comp.py comps/desktop.json --restart
```

The script typesets text layers with PostScript names, crops images to their boxes, adds grain when asked and saves a layered PSD plus PNG. It stops before creating a document when Photoshop lacks a font, and `--restart` restarts Photoshop only when it has no open documents. Without Photoshop (or off Windows) build a static HTML comp with the same `fonts.css` and screenshot it. Look at the comps and fix direction problems now. A person may refine the PSD; re-export the PNG and treat it as the reference.

## 7. Implement

Give the implementer the brief, the material, DESIGN.md and the comp PNGs. Section order follows `direction.narrative`; adding a section the comp lacks needs a reason. Use `fonts.css` (or `designmd.py export --format css-fonts`) and the token export through the project's existing stack, with `font-synthesis: none`. Keep the Korean copy free of em/en dashes and spaced hyphen connectors, and keep one speech level.

## 8. Verify

```text
python scripts/audit.py http://127.0.0.1:8000/ --widths 1440,390 --out <dir>
```

Serve the page (`python -m http.server 8000 --bind 127.0.0.1` in the site folder); `file://` blocks preloaded fonts and adds false console errors. Resolve every error (`font-fallback`, `overflow-x`). Fix each warning or justify it from DESIGN.md; a skipped check is not a pass. Compare the screenshots with the comps and list the differences. Run the project's own checks and use the page in a real browser. For a substantial page, have the model that did not implement it review against the brief and DESIGN.md and report violations only. Designer polish skills may review spacing, type and motion, but a recorded direction choice is not a defect. Read [references/review.md](references/review.md) for the tells catalog, copy rewrites, cross-model review prompt and blind test.

## 9. Record and report

```text
python scripts/direction.py record --project "<name>" --pick direction.json --ledger ~/.claude/design-ledger.json
```

Report the direction and why, fonts with license and verified date, which images are generated and which are original, audit counts including skipped checks, comp versus build differences, and what is still missing.

## Tool notes

- The landing fork lives at https://github.com/cateyelow/design.md (branch `landing`). `designmd.py` looks for it in `$DESIGNMD_FORK`, `~/GitHub/design.md` and `C:/GitHub/design.md`; without it the upstream CLI runs and the fonts, direction and palette rules are missing. Setup: `git clone -b landing https://github.com/cateyelow/design.md` then `bun install` in `packages/cli`.
- On Windows the `design.md` binary name collides with the Markdown file association; the scripts always call the dot-free `designmd` entry.
- `photoshop_comp.py` uses Photoshop COM (Windows, pywin32). ExtendScript is ES3, so the spec is passed as a literal; the script never quits Photoshop while documents are open.
- If Adobe Fonts already activates a family with the same PostScript name as an installed file, Photoshop may use the Adobe copy. Deactivate it in Creative Cloud so the comp and the site use the same file.

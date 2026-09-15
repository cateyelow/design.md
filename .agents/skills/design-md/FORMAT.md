# DESIGN.md: format and philosophy (cached reference)

Schema guidance from [`google-labs-code/design.md`](https://github.com/google-labs-code/design.md) 0.4.0 plus the landing fork [`cateyelow/design.md`](https://github.com/cateyelow/design.md) (branch `landing`, package `@cateyelow/design.md` `0.4.0-landing.1`), checked September 2026. The fork adds `fonts` and `direction` and five rules; everything else matches upstream 0.4.0. For an existing project on another CLI version, keep that version and inspect its `spec` and lint output.

## Philosophy: the actual leverage

> **The quality of a generated design is determined less by the precision of its values than by how clearly the intent is described.**

- **A specific reference carries more than a list of adjectives.** "A 1970s graduate CS lecture handout in the tradition of an old, established university" evokes a whole world: one ink colour, generous margins, a serif at reading size, no decoration. "Modern, clean, trustworthy, premium" describes a region, and the model lands in its generic centre.
- **Prose, not tokens, is the focus.** Token values are context the prose refers to. Document the nature of the design in prose and let established tools render.
- **Negative constraints arrive for free.** Naming the reference names what it is not. A short, intentional Do's and Don'ts complements a strong reference; a long list means the reference was too vague.
- **A direction is chosen, not defaulted.** Record why this project looks the way it does and how it differs from recent work, so later edits and reviewers keep the character instead of polishing it back to the average.

Example Overview:

> A graduate-level computer science lecture handout in the tradition of an old established university… austere, informationally dense, and proudly unconcerned with first impressions. The audience knows why they are there and the handout's job is to do work, not to seduce.

## File shape

1. **Optional YAML frontmatter** between a line of exactly `---` and a closing `---`. When present, these are the normative values.
2. **Markdown body**: prose rationale under `##` headings. Prose may use descriptive colour names that map to token names.

## Section order

Omit sections that do not apply; keep the present ones in this order (all `##`):

1. **Overview** (aka "Brand & Style")
2. **Colors**
3. **Typography**
4. **Layout** (aka "Layout & Spacing")
5. **Elevation & Depth** (aka "Elevation")
6. **Shapes**
7. **Components**
8. **Do's and Don'ts**

## Token schema (frontmatter)

```yaml
version: alpha          # optional
name: <string>
description: <string>   # optional
omitted: <list>         # optional: intentionally omitted token sections
colors:
  <token>: <CSS color>              # at least `primary`
typography:
  <token>:
    fontFamily: <string>            # first family must be declared in `fonts` (fork)
    fontSize: <Dimension>
    fontWeight: <number>
    lineHeight: <Dimension | number>  # unitless = multiplier of fontSize (preferred)
    letterSpacing: <Dimension>
    fontFeature: <string>           # optional, font-feature-settings
    fontVariation: <string>         # optional, font-variation-settings
rounded:
  <scale>: <Dimension>
spacing:
  <scale>: <Dimension | number>
components:
  <name>:
    backgroundColor: <color | {ref}>
    textColor: <color | {ref}>
    typography: "{typography.<name>}"
    rounded: "{rounded.<scale>}"
    padding | size | height | width: <Dimension | value>
fonts:                              # fork
  <token>:
    family: <string>                # CSS family name used in typography
    source: <url>                   # official distribution
    license: <string>               # OFL-1.1, Custom commercial-free, Proprietary, ...
    licenseUrl: <url>               # optional
    webEmbedding: <boolean>         # false: comps and images only, never @font-face
    verified: "YYYY-MM-DD"          # date the license text was read
    files:                          # optional
      - path: <path as served>
        weight: <400 | "100 900">
        style: normal | italic
        format: woff2 | woff | truetype | opentype
    stylesheet: <path>              # optional: a ready stylesheet (sliced Google faces); css-fonts emits @import
    display: swap                   # optional
    unicodeRange: <string>          # optional
    fallback: <CSS stack>           # optional
direction:                          # fork; every value a string, extra keys allowed
  narrative: <what persuades, in section order>
  world: <the reference object or medium>
  layout: <archetype and reading order>
  type: <pairing id and why; name any default typeface on purpose here>
  color: <strategy>
  image: <physical treatment and what is generated vs original>
  density: <space vs information>
  motion: <how much moves>
  tone: <who is speaking>
  reason: <why this direction answers the brief>
  colorSource: <photo:<file> | catalog:wada#<n> | brand:<guide> | reference:<url>, as printed by palette.py roles>
  differs: <how it differs from recent ledger entries>
```

- **Color**: any valid CSS colour (hex, named, `rgb()`/`hsl()`/`hwb()`, `oklch()`/`oklab()`/`lch()`/`lab()`, `color-mix()`). Hex is the recommended default. All convert to sRGB for contrast checks.
- **Dimension**: a number with `px`, `em` or `rem`.
- **Token reference**: `{path.to.token}` pointing at a primitive, except inside `components`, where composite refs like `{typography.label-md}` are allowed.
- **Variants** (hover, active) are separate component entries such as `button-primary-hover`.
- `scripts/fonts.py design-block` prints a `fonts` block from `fonts.lock.json` with the catalog's license fields. Record Adobe Fonts desktop faces and KoPubWorld with `webEmbedding: false`; record a user-supplied paid font only with its web license.

## CLI

Run through the skill's wrapper, which finds the fork clone (`$DESIGNMD_FORK`, `~/GitHub/design.md`, `C:/GitHub/design.md`) and falls back to `npx -y -p @google/design.md@0.4.0 designmd` with a warning:

```text
python scripts/designmd.py lint DESIGN.md
python scripts/designmd.py export --format css-fonts DESIGN.md
python scripts/designmd.py --where
```

| Command | What it does | Notes |
|---|---|---|
| `lint DESIGN.md` | Validate structure and tokens. | JSON `findings[]` `{severity, path?, message}` and `summary {errors, warnings, infos}`. Exit 1 while `errors > 0`. **Gate: errors = 0.** |
| `export --format <fmt> DESIGN.md` | Emit tokens. | `css-tailwind` (Tailwind v4 `@theme`), `json-tailwind`/`tailwind` (v3 `theme.extend`), `dtcg` (W3C Design Tokens), `css-vars`, and in the fork `css-fonts` (one `@font-face` per file plus `--font-<token>` variables; an entry with `stylesheet` and no `files` becomes an `@import`; entries with `webEmbedding: false` become a skip comment). Export exits 0 even with lint findings. |
| `diff OLD NEW` | Token and section changes. | Read the JSON changes; a nonzero exit is not proof that a token change is invalid. |
| `spec` | Emit the format spec. | Includes `fonts` and `direction` in the fork. |

Upstream checks: unresolved references, section order, missing token groups, component token-pair contrast, orphaned tokens, likely key typos. Token-pair contrast is not an audit of the rendered page.

Fork rules:

| Rule | Severity | Fires when |
|---|---|---|
| `font-license` | error | a family used by typography has `webEmbedding: false`, or a `fonts` entry is malformed |
| `font-license` | warning | typography uses a non-generic family not declared in `fonts`, or `verified` is not a real date |
| `generic-typeface` | warning, info | Inter, Geist, Space Grotesk, Instrument Serif, Poppins, Montserrat, Roboto, Open Sans, DM Sans, Plus Jakarta Sans or Manrope is used; info when `direction.type` names it |
| `single-family` | info | three or more typography tokens all use one family (fine when intentional) |
| `ai-palette` | warning, info | a violet colour paired with a cyan-blue one; info when `primary` alone is violet; warning when the colours are an off-white paper, a near-black ink and at most one warm accent, unless `direction.colorSource` names a source other than `model` |
| `direction-record` | info, warning | info when `direction` is absent or has no `colorSource`; warning when `narrative`, `layout` or `image` is missing or empty, or a value is not a string |

## Authoring checklist

- [ ] Overview names a specific reference world and the reason it fits this business.
- [ ] `direction` has all nine axes plus `reason`, `differs` and `colorSource`, and every colour token traces to that source.
- [ ] `colors.primary` defined; prose gives each colour a role.
- [ ] Every typography family is declared in `fonts` with source, license, `webEmbedding` and `verified`.
- [ ] Sections in canonical order; only the ones the work needs.
- [ ] Every `{...}` reference resolves.
- [ ] Short Do's and Don'ts naming the tells this direction is most likely to slide into.
- [ ] `lint` gives `summary.errors: 0`; `generic-typeface`, `ai-palette` and `direction-record` warnings are fixed or explained in `direction`.

<!--
Copyright 2026 cateyelow

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

# Landing-page fork

This fork extends [google-labs-code/design.md](https://github.com/google-labs-code/design.md),
licensed under [Apache-2.0](LICENSE). Upstream notices are retained; modified source
files identify the landing changes.

The CLI package is `@cateyelow/design.md`, version `0.4.0-landing.1`.
Both executable names, `design.md` and `designmd`, are retained.

## Additions

- Optional `fonts` frontmatter records font families, official distribution URLs,
  licenses, web embedding permission, verification dates, and local font files.
  Optional display, Unicode range, and fallback settings control CSS output.
- Optional `direction` frontmatter records narrative, world, layout, type, color,
  colorSource, image, density, motion, tone, reason, and what differs for this project.
  `direction.colorSource` records where the color values came from: project
  material or a sourced palette, such as `photo:storefront.jpg`, `catalog:<id>`,
  `brand:<guide>`, or `reference:<url>`. The `direction-record` rule adds an info
  finding when this field is missing or blank in a direction record.
  Additional string fields and unknown top-level keys remain allowed.
- Five additional rules: `font-license` (warning/error), `generic-typeface`
  (warning/info), `single-family` (info), `ai-palette` (warning/info), and
  `direction-record` (info/warning).
  `ai-palette` warns for violet paired with cyan-blue and notes a violet primary
  on its own. It also warns for the palette models fall back to: off-white paper,
  near-black ink, and at most one warm accent, including palettes with no accent.
  This check uses D65 CIELAB lightness and chroma to identify light and dark
  neutrals, and groups chromatic colors within 30 degrees of each hue family's
  first member. It matches only when there are no chromatic colors or one warm
  hue family. Take these color values from the project's material or a sourced
  palette and record the source in `direction.colorSource`. A non-empty source
  that does not start with `model` (case-insensitive, after trimming whitespace)
  suppresses this check. `model` and `model: chosen by hand` still warn. The
  violet findings are unaffected by the source.
- `export --format css-fonts` emits one `@font-face` block per file followed by
  `:root` font variables. It preserves file paths and skips fonts with
  `webEmbedding: false`, emitting a CSS comment for each. Malformed font metadata
  produces lint findings and is skipped by the exporter. An entry that carries
  `stylesheet` and no `files`, as a distribution sliced by unicode range does,
  emits one `@import` ahead of every other rule.

See the generated [specification](docs/spec.md) for field definitions and
[LANDING_FONTS.md](packages/cli/src/linter/fixtures/LANDING_FONTS.md) for a complete
example. The fixture contains illustrative metadata and paths; font binaries
are not included.

## The landing skill

`.agents/skills/design-md` holds the landing-page skill that drives this CLI:
a direction ledger, a font catalog with license metadata and a fetcher, a
Photoshop comp builder, and a rendered-page audit. Install it into a project
with `npx skills add "cateyelow/design.md#landing"` (the branch suffix matters: the CLI clones the default branch otherwise); the scripts need Python 3.11 with
fontTools, Playwright with installed Google Chrome for the audit, and (only for
comps) Windows with Photoshop and pywin32.

## Run from a clone

From the repository root, install dependencies:

```bash
cd packages/cli
bun install
cd ../..
```

Then lint a project file or export its font CSS:

```bash
bun run packages/cli/src/index.ts lint DESIGN.md
bun run packages/cli/src/index.ts export DESIGN.md --format css-fonts
```

To try the included fixture:

```bash
bun run packages/cli/src/index.ts lint packages/cli/src/linter/fixtures/LANDING_FONTS.md --format json
bun run packages/cli/src/index.ts export packages/cli/src/linter/fixtures/LANDING_FONTS.md --format css-fonts
```

Lint exits with code 1 when it finds errors. Successful exports exit with code 0
even when the source has lint findings; run lint separately as the validation step.
Invalid export formats or emitter failures exit with code 1, and unreadable input
files exit with code 2.

## Development

From `packages/cli`:

```bash
bun test
bun run lint
bun run spec:gen
bun run build
```

The build copies generated assets with `cp`; Git Bash can run it on Windows.


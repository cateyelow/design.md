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
  image, density, motion, tone, reason, and what differs for this project.
  Additional string fields and unknown top-level keys remain allowed.
- Five additional rules: `font-license` (warning/error), `generic-typeface`
  (warning/info), `single-family` (info), `ai-palette` (warning/info), and
  `direction-record` (info/warning).
- `export --format css-fonts` emits one `@font-face` block per file followed by
  `:root` font variables. It preserves file paths and skips fonts with
  `webEmbedding: false`, emitting a CSS comment for each. Malformed font metadata
  produces lint findings and is skipped by the exporter.

See the generated [specification](docs/spec.md) for field definitions and
[LANDING_FONTS.md](packages/cli/src/linter/fixtures/LANDING_FONTS.md) for a complete
example. The fixture contains illustrative metadata and paths; font binaries
are not included.

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


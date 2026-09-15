---
# Copyright 2026 cateyelow
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
name: Landing Fonts
colors:
  primary: "#24463e"
  surface: "#faf7f0"
  on-surface: "#192820"
typography:
  headline-display:
    fontFamily: '"Public Sans", system-ui, sans-serif'
    fontSize: 3rem
    fontWeight: 700
  body-md:
    fontFamily: '"Public Sans", system-ui, sans-serif'
    fontSize: 1rem
    fontWeight: 400
fonts:
  text:
    family: Public Sans
    source: https://public-sans.digital.gov/
    license: OFL-1.1
    licenseUrl: https://github.com/uswds/public-sans/blob/develop/LICENSE.md
    webEmbedding: true
    verified: "2026-09-15"
    files:
      - path: ./fonts/PublicSans-Variable.woff2
        weight: "100 900"
        format: woff2
      - path: ./fonts/PublicSans-Italic.woff2
        weight: "100 900"
        style: italic
    display: swap
    unicodeRange: U+0000-00FF
    fallback: system-ui, sans-serif
  reference:
    family: Example Reference Face
    source: https://example.org/reference-font
    license: Proprietary
    webEmbedding: false
    verified: "2026-09-15"
    files:
      - path: ./reference-only.otf
direction:
  narrative: A field journal for neighborhood walks.
  world: Local guides and printed trail notes.
  layout: Wide story columns with compact route details.
  type: Public Sans connects the guide with civic wayfinding.
  color: Forest ink on warm paper.
  image: Documentary photographs of streets and trees.
  density: Spacious stories and compact route facts.
  motion: Short fades that respect reduced motion.
  tone: Observant and welcoming.
  reason: Make unfamiliar routes feel approachable.
  differs: Street-level photographs and annotated maps lead the page.
  custom: Leave room for seasonal trail notes.
spacing:
  unit: 8px
rounded:
  sm: 4px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.surface}"
    typography: "{typography.body-md}"
    rounded: "{rounded.sm}"
---

## Overview

A landing-page fixture for a neighborhood walking guide. Font paths and license
verification dates are illustrative test data; no font binaries are bundled.

## Colors

Forest ink and warm paper keep maps and photographs readable.

## Typography

Public Sans uses weight and size to distinguish headings from route descriptions.

## Layout

Wide story columns alternate with short route summaries.

## Elevation & Depth

Thin borders divide content.

## Shapes

Small corner radii soften controls.

## Components

Primary buttons open the featured route.

## Do's and Don'ts

Use documentary images. Keep route instructions brief.


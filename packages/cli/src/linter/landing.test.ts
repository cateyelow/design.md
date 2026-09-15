// Copyright 2026 cateyelow
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import { it, expect } from 'bun:test';
import { ParserHandler } from './parser/handler.js';
import { SCHEMA_KEYS } from './parser/spec.js';
import { ModelHandler } from './model/handler.js';

it('preserves landing metadata through parsing and model building while allowing extensions', () => {
  const result = new ParserHandler().execute({ content: `---
fonts:
  text:
    family: Public Sans
    source: https://public-sans.digital.gov/
    license: OFL-1.1
    webEmbedding: true
    verified: 2026-09-15
    files:
      - path: ./fonts/text.woff2
direction:
  narrative: A local journal
  layout: Wide editorial columns
  image: Documentary photographs
  custom: Project-specific guidance
extension: custom metadata
---` });
  expect(result.success).toBe(true);
  if (!result.success) return;
  expect(SCHEMA_KEYS).toContain('fonts');
  expect(SCHEMA_KEYS).toContain('direction');
  expect(result.data.fonts).toMatchObject({ text: { family: 'Public Sans', verified: '2026-09-15' } });
  expect(result.data.direction).toMatchObject({ custom: 'Project-specific guidance' });
  const model = new ModelHandler().execute(result.data);
  expect(model.designSystem.fonts).toEqual(result.data.fonts);
  expect(model.designSystem.direction).toEqual(result.data.direction);
  expect(model.designSystem.unknownKeys).toEqual(['extension']);
  expect(model.findings).toEqual([]);
});


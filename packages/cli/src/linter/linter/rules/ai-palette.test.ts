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

import { describe, it, expect } from 'bun:test';
import { aiPaletteRule } from './ai-palette.js';
import { buildState } from './test-helpers.js';
import { ModelHandler } from '../../model/handler.js';

describe('ai-palette', () => {
  it('emits info for a violet primary without a cyan-blue partner', () => {
    const findings = aiPaletteRule.run(buildState({ colors: { accent: '#8040bf', primary: '#8040bf', neutral: '#777777' } }));
    expect(findings).toHaveLength(1);
    expect(findings[0]).toMatchObject({ path: 'colors.primary', severity: 'info' });
    expect(aiPaletteRule.run(buildState({ colors: { accent: '#8040bf', primary: '#777777' } }))).toEqual([]);
  });
  it('warns for violet with cyan-blue across CSS formats and ignores other palettes', () => {
    for (const colors of [
      { purple: '#8040bf', blue: '#40bfbf' },
      { purple: 'hsl(270 50% 50%)', blue: 'rgb(64, 149, 191)' },
      // These boundary hues survive the existing parser's 8-bit RGB rounding.
      { purple: 'hsl(250 100% 60%)', blue: 'hsl(235 100% 60%)' },
      { purple: 'hsl(300 100% 50%)', blue: 'hsl(180 100% 50%)' },
    ]) {
      const findings = aiPaletteRule.run(buildState({ colors }));
      expect(aiPaletteRule.severity).toBe('warning');
      expect(findings).toHaveLength(1);
      expect(findings[0]?.path).toBe('colors.purple');
      expect(findings[0]?.message).toContain('purple');
      expect(findings[0]?.message).toContain('blue');
    }
    for (const purple of ['hsl(249 50% 50%)', 'hsl(301 50% 50%)', 'hsl(270 44% 50%)', 'hsl(270 60% 24%)', 'hsl(270 60% 81%)', '#777777']) {
      expect(aiPaletteRule.run(buildState({ colors: { purple, blue: 'hsl(210 60% 50%)' } }))).toEqual([]);
    }
    const model = new ModelHandler().execute({ sourceMap: new Map(), colors: { purple: 'invalid', blue: '#0080ff' } });
    expect(aiPaletteRule.run(model.designSystem)).toEqual([]);
    expect(aiPaletteRule.run(buildState())).toEqual([]);
  });
});

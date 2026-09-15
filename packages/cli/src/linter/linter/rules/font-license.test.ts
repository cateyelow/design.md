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
import { fontLicenseRule } from './font-license.js';
import { buildState } from './test-helpers.js';

describe('font-license', () => {
  it('validates optional font and file values without throwing on malformed maps or entries', () => {
    for (const fonts of [null, false, 'font', []]) {
      expect(fontLicenseRule.run(buildState({ fonts }))).toContainEqual(expect.objectContaining({ path: 'fonts', severity: 'error' }));
    }
    const entry = { family: 'Lora', source: 'https://example.org', license: 'OFL-1.1', webEmbedding: true, verified: '2026-09-15' };
    for (const [field, value, path] of [
      ['licenseUrl', 42, 'licenseUrl'], ['display', 'bad', 'display'],
      ['unicodeRange', [], 'unicodeRange'], ['fallback', false, 'fallback'],
      ['files', {}, 'files'], ['files', [null], 'files.0'],
      ['files', [{}], 'files.0.path'], ['files', [{ path: 42 }], 'files.0.path'],
      ['files', [{ path: 'x.woff', weight: false }], 'files.0.weight'],
      ['files', [{ path: 'x.woff', style: 'oblique' }], 'files.0.style'],
      ['files', [{ path: 'x.woff', format: 'ttf' }], 'files.0.format'],
    ] as const) {
      expect(fontLicenseRule.run(buildState({ fonts: { text: { ...entry, [field]: value } } }))).toContainEqual(expect.objectContaining({ path: `fonts.text.${path}`, severity: 'error' }));
    }
    for (const value of [null, 'Lora', [], false]) {
      expect(fontLicenseRule.run(buildState({ fonts: { text: value } }))).toContainEqual(expect.objectContaining({ path: 'fonts.text.family', severity: 'error' }));
    }
    expect(fontLicenseRule.run(buildState({ fonts: { text: { ...entry, files: [{ path: './x.woff2', weight: '100 900', style: 'italic', format: 'woff2' }], display: 'optional', unicodeRange: 'U+0000-00FF', fallback: 'serif', licenseUrl: 'https://example.org/license' } } }))).toEqual([]);
  });
  it('warns for missing or impossible verification dates and accepts real leap days', () => {
    const entry = { family: 'Lora', source: 'https://example.org', license: 'OFL-1.1', webEmbedding: true };
    for (const verified of [undefined, null, 20260915, '', '2026-9-15', '2026-02-29', '2026-04-31', '2026-13-01', '1900-02-29', '2026-00-10', '2026-01-00', '2026-09-15T00:00:00Z']) {
      expect(fontLicenseRule.run(buildState({ fonts: { text: { ...entry, verified } } }))).toContainEqual(expect.objectContaining({ path: 'fonts.text.verified', severity: 'warning' }));
    }
    for (const verified of ['2026-09-15', '2024-02-29', '2000-02-29']) {
      expect(fontLicenseRule.run(buildState({ fonts: { text: { ...entry, verified } } }))).toEqual([]);
    }
  });
  it('matches declared families case-insensitively and rejects used fonts without embedding permission', () => {
    const text = { family: 'PUBLIC SANS', source: 'https://example.org', license: 'Proprietary', webEmbedding: false, verified: '2026-09-15' };
    const typography = { title: { fontFamily: " 'Public Sans' , serif" }, body: { fontFamily: 'Lora, serif' }, generic: { fontFamily: 'system-ui, Lora' } };
    const findings = fontLicenseRule.run(buildState({ fonts: { text }, typography }));
    expect(findings).toHaveLength(2);
    expect(findings).toContainEqual(expect.objectContaining({ path: 'fonts.text.webEmbedding', severity: 'error' }));
    expect(findings).toContainEqual(expect.objectContaining({ path: 'typography.body.fontFamily' }));
    expect(fontLicenseRule.run(buildState({ fonts: { text } }))).toEqual([]);
    expect(fontLicenseRule.run(buildState({ typography: { body: { fontFamily: 'sans-serif, Lora' } } }))).toEqual([]);
    expect(fontLicenseRule.run(buildState({ fonts: {}, typography: { body: { fontFamily: 'Lora' } } }))[0]?.path).toBe('typography.body.fontFamily');
  });
  it('reports missing and wrongly typed required metadata at field paths', () => {
    for (const field of ['family', 'source', 'license', 'webEmbedding']) {
      for (const value of [undefined, null, [], {}, 42, field === 'webEmbedding' ? 'false' : false]) {
        const entry = { family: 'Lora', source: 'https://example.org/fonts', license: 'OFL-1.1', webEmbedding: true, verified: '2026-09-15', [field]: value };
        const findings = fontLicenseRule.run(buildState({ fonts: { text: entry } }));
        expect(findings).toContainEqual(expect.objectContaining({ path: `fonts.text.${field}`, severity: 'error' }));
      }
    }
    expect(fontLicenseRule.run(buildState({ fonts: { text: {
      family: 'Lora', source: 'https://example.org/fonts', license: 'OFL-1.1', webEmbedding: true, verified: '2026-09-15',
    } } }))).toEqual([]);
  });
  it('warns once when custom families are used without fonts metadata', () => {
    const findings = fontLicenseRule.run(buildState({
      typography: { title: { fontFamily: '"Public Sans", serif' }, body: { fontFamily: 'Lora' } },
    }));
    expect(fontLicenseRule.severity).toBe('warning');
    expect(findings).toHaveLength(1);
    expect(findings[0]?.path).toBe('fonts');
  });
});

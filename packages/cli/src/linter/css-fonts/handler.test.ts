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
import { CssFontsEmitterHandler } from './handler.js';
import { buildState } from '../linter/rules/test-helpers.js';

const entry = {
  family: 'Public Sans', source: 'https://public-sans.digital.gov/', license: 'OFL-1.1',
  webEmbedding: true, verified: '2026-09-15',
};

describe('CssFontsEmitterHandler', () => {
  it('quotes CSS family names and omits hints for unknown file extensions', () => {
    const result = new CssFontsEmitterHandler().execute(buildState({ fonts: {
      text: { ...entry, family: 'Text "Editorial"', files: [{ path: './download.constructor' }] },
    } }));
    expect(result.success).toBe(true);
    if (!result.success) return;
    expect(result.data.css).toContain('font-family: "Text \\"Editorial\\"";');
    expect(result.data.css).toContain('--font-text: "Text \\"Editorial\\"";');
    expect(result.data.css).toContain('src: url("./download.constructor");');
  });
  it('keeps export successful for malformed metadata while lint reports findings', () => {
    for (const fonts of [undefined, null, [], 'text', { text: null }, { text: { ...entry, files: [null] } }, { text: { ...entry, family: false } }, { text: { ...entry, display: 42 } }]) {
      expect(new CssFontsEmitterHandler().execute(buildState({ fonts }))).toEqual({
        success: true, data: { css: ':root {\n}\n' },
      });
    }
    const result = new CssFontsEmitterHandler().execute(buildState({ fonts: { text: { ...entry, verified: false, files: [{ path: '../Text.WOFF2?v=1#latin' }] } } }));
    expect(result.success).toBe(true);
    if (result.success) expect(result.data.css).toContain('src: url("../Text.WOFF2?v=1#latin") format("woff2");');
  });
  it('respects explicit formats, display, unicode range, and embedding restrictions', () => {
    const result = new CssFontsEmitterHandler().execute(buildState({ fonts: {
      blocked: { ...entry, webEmbedding: false, files: [{ path: 'blocked.woff' }] },
      text: { ...entry, display: 'fallback', unicodeRange: 'U+0000-00FF', files: [{ path: './fonts/download?v=2#font', format: 'woff2' }] },
    } }));
    expect(result.success).toBe(true);
    if (!result.success) return;
    expect(result.data.css).toStartWith('/* skipped blocked: webEmbedding is false */\n');
    expect(result.data.css).not.toContain('--font-blocked');
    expect(result.data.css).not.toContain('blocked.woff');
    expect(result.data.css).toContain('src: url("./fonts/download?v=2#font") format("woff2");');
    expect(result.data.css).toContain('font-display: fallback;');
    expect(result.data.css).toContain('unicode-range: U+0000-00FF;');
  });
  it('imports a stylesheet for a sliced distribution and keeps files authoritative', () => {
    const result = new CssFontsEmitterHandler().execute(buildState({ fonts: {
      sliced: { ...entry, stylesheet: './assets/fonts/fonts.css' },
      sliced2: { ...entry, family: 'Sliced Two', stylesheet: './assets/fonts/fonts.css' },
      both: { ...entry, family: 'Both', stylesheet: './ignored.css', files: [{ path: './both.woff2' }] },
    } }));
    expect(result.success).toBe(true);
    if (!result.success) return;
    expect(result.data.css).toStartWith('@import url("./assets/fonts/fonts.css");\n');
    expect(result.data.css.match(/@import/g)).toHaveLength(1);
    expect(result.data.css).not.toContain('ignored.css');
    expect(result.data.css).toContain('--font-sliced:');
    expect(result.data.css).toContain('src: url("./both.woff2") format("woff2");');
  });
  it('emits one face per file with inferred formats, defaults, and font variables', () => {
    const result = new CssFontsEmitterHandler().execute(buildState({ fonts: {
      text: { ...entry, fallback: 'system-ui, sans-serif', files: [
        { path: './fonts/Text.woff2' }, { path: '../Text.woff', weight: 700, style: 'italic' },
        { path: '/assets/Text.ttf', weight: '100 900' }, { path: 'Text.otf' },
      ] },
      display: { ...entry, family: 'Lora' },
    } }));
    expect(result.success).toBe(true);
    if (!result.success) return;
    expect(result.data.css).toBe(`@font-face {
  font-family: "Public Sans";
  src: url("./fonts/Text.woff2") format("woff2");
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}

@font-face {
  font-family: "Public Sans";
  src: url("../Text.woff") format("woff");
  font-weight: 700;
  font-style: italic;
  font-display: swap;
}

@font-face {
  font-family: "Public Sans";
  src: url("/assets/Text.ttf") format("truetype");
  font-weight: 100 900;
  font-style: normal;
  font-display: swap;
}

@font-face {
  font-family: "Public Sans";
  src: url("Text.otf") format("opentype");
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}

:root {
  --font-text: "Public Sans", system-ui, sans-serif;
  --font-display: "Lora";
}
`);
  });
});

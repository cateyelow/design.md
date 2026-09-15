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

import type { CssFontsEmitterSpec, CssFontsEmitterResult } from './spec.js';
import type { DesignSystemState } from '../model/spec.js';
import { FontEntrySchema, isRecord } from '../model/font.js';

const EXTENSION_FORMATS = new Map([
  ['woff2', 'woff2'], ['woff', 'woff'], ['ttf', 'truetype'], ['otf', 'opentype'],
]);

/** Emits font faces and variables from validated metadata; malformed entries are lint findings. */
export class CssFontsEmitterHandler implements CssFontsEmitterSpec {
  execute(state: DesignSystemState): CssFontsEmitterResult {
    try {
      const blocks: string[] = [];
      const variables: string[] = [];
      for (const [token, raw] of Object.entries(isRecord(state.fonts) ? state.fonts : {})) {
        if (isRecord(raw) && raw.webEmbedding === false) {
          blocks.push(`/* skipped ${token.replace(/\*\//g, '* /')}: webEmbedding is false */`);
          continue;
        }
        const result = FontEntrySchema.safeParse(raw);
        if (!result.success) continue;
        const entry = result.data;
        const family = quoteFamily(entry.family);
        for (const file of entry.files ?? []) {
          const extension = file.path.split(/[?#]/)[0]?.split('.').pop()?.toLowerCase() ?? '';
          const format = file.format ?? EXTENSION_FORMATS.get(extension);
          blocks.push([
            '@font-face {',
            `  font-family: ${family};`,
            `  src: url("${file.path}")${format ? ` format("${format}")` : ''};`,
            `  font-weight: ${file.weight ?? 400};`,
            `  font-style: ${file.style ?? 'normal'};`,
            `  font-display: ${entry.display ?? 'swap'};`,
            ...(entry.unicodeRange === undefined ? [] : [`  unicode-range: ${entry.unicodeRange};`]),
            '}',
          ].join('\n'));
        }
        variables.push(`  --font-${token}: ${family}${entry.fallback ? `, ${entry.fallback}` : ''};`);
      }
      blocks.push([':root {', ...variables, '}'].join('\n'));
      return { success: true, data: { css: blocks.join('\n\n') + '\n' } };
    } catch (error) {
      return { success: false, error: { code: 'CSS_FONTS_ERROR', message: error instanceof Error ? error.message : String(error) } };
    }
  }
}

function quoteFamily(value: string): string {
  const escaped = value.replace(/["\\\n\r\f]/g, character =>
    character === '"' || character === '\\'
      ? '\\' + character
      : '\\' + character.charCodeAt(0).toString(16) + ' ',
  );
  return '"' + escaped + '"';
}

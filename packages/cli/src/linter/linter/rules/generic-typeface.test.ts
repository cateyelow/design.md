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
import { genericTypefaceRule } from './generic-typeface.js';
import { buildState } from './test-helpers.js';

describe('generic-typeface', () => {
  it('downgrades only families named in direction.type and tolerates malformed direction', () => {
    const typography = { title: { fontFamily: 'Inter' }, body: { fontFamily: 'Roboto' } };
    const findings = genericTypefaceRule.run(buildState({ typography, direction: { type: 'INTER keeps our existing brand voice.' } }));
    expect(findings[0]?.severity).toBe('info');
    expect(findings[1]?.severity ?? genericTypefaceRule.severity).toBe('warning');
    for (const direction of [undefined, null, [], 'Inter', { type: 42 }, { type: null }]) {
      expect(genericTypefaceRule.run(buildState({ typography, direction }))[0]?.severity ?? genericTypefaceRule.severity).toBe('warning');
    }
  });
  it('warns once per default family at its first token and ignores other families', () => {
    for (const family of ['Inter', 'Geist', 'Geist Sans', 'Space Grotesk', 'Instrument Serif', 'Poppins', 'Montserrat', 'Roboto', 'Open Sans', 'DM Sans', 'Plus Jakarta Sans', 'Manrope']) {
      const findings = genericTypefaceRule.run(buildState({ typography: {
        title: { fontFamily: ` "${family.toUpperCase()}" , serif` },
        body: { fontFamily: family.toLowerCase() },
        caption: { fontFamily: 'Public Sans' },
      } }));
      expect(genericTypefaceRule.severity).toBe('warning');
      expect(findings).toHaveLength(1);
      expect(findings[0]?.path).toBe('typography.title.fontFamily');
      expect(findings[0]?.message).toContain('direction.type');
    }
    expect(genericTypefaceRule.run(buildState({ typography: { body: { fontFamily: 'Lora, Inter' } } }))).toEqual([]);
  });
});

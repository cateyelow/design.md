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

import type { RuleDescriptor, RuleFinding } from './types.js';
import { firstFamily, isRecord } from '../../model/font.js';

const DEFAULT_FAMILIES = new Set([
  'inter', 'geist', 'geist sans', 'space grotesk', 'instrument serif', 'poppins',
  'montserrat', 'roboto', 'open sans', 'dm sans', 'plus jakarta sans', 'manrope',
]);

export const genericTypefaceRule: RuleDescriptor = {
  name: 'generic-typeface',
  severity: 'warning',
  description: 'Flags common generated-page typefaces; records intentional choices as info.',
  run(state): RuleFinding[] {
    const seen = new Set<string>();
    const findings: RuleFinding[] = [];
    const rationale = isRecord(state.direction) && typeof state.direction.type === 'string'
      ? state.direction.type.toLowerCase() : '';
    for (const [token, typography] of state.typography) {
      const family = firstFamily(typography.fontFamily);
      const key = family.toLowerCase();
      if (!DEFAULT_FAMILIES.has(key) || seen.has(key)) continue;
      seen.add(key);
      findings.push({
        path: `typography.${token}.fontFamily`,
        severity: rationale.includes(key) ? 'info' : 'warning',
        message: `${family}: these defaults make generated pages look alike; state the reason in direction.type if the choice is intentional.`,
      });
    }
    return findings;
  },
};

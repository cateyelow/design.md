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
import { firstFamily, GENERIC_FAMILIES, isRecord, FontEntrySchema } from '../../model/font.js';

export const fontLicenseRule: RuleDescriptor = {
  name: 'font-license',
  severity: 'warning',
  description: 'Checks font distribution, license metadata, verification dates, and web embedding permission.',
  run(state): RuleFinding[] {
    const used = [...state.typography].filter(([, token]) => {
      const family = firstFamily(token.fontFamily).toLowerCase();
      return family && !GENERIC_FAMILIES.has(family);
    });
    if (state.fonts === undefined && used.length > 0) {
      return [{ path: 'fonts', message: 'Declare fonts with source, license, webEmbedding, and verified metadata for the non-generic families used by typography.' }];
    }
    if (state.fonts === undefined) return [];
    if (!isRecord(state.fonts)) {
      return [{ path: 'fonts', severity: 'error', message: 'fonts must be a map of font token names to objects.' }];
    }
    const findings: RuleFinding[] = [];
    const declared = new Set<string>();
    const usedFamilies = new Set(used.map(([, token]) => firstFamily(token.fontFamily).toLowerCase()));
    for (const [name, entry] of Object.entries(state.fonts)) {
      if (!isCalendarDate(isRecord(entry) ? entry.verified : undefined)) {
        findings.push({ path: `fonts.${name}.verified`, severity: 'warning', message: 'verified must be a real calendar date in YYYY-MM-DD recording when the license was checked.' });
      }
      if (isRecord(entry) && typeof entry.family === 'string') {
        const family = entry.family.trim().toLowerCase();
        declared.add(family);
        if (entry.webEmbedding === false && usedFamilies.has(family)) {
          findings.push({ path: `fonts.${name}.webEmbedding`, severity: 'error', message: `${entry.family} cannot ship as a web font: webEmbedding is false.` });
        }
      }
      const result = FontEntrySchema.safeParse(isRecord(entry) ? entry : {});
      if (!result.success) {
        for (const issue of result.error.issues) {
          findings.push({ path: `fonts.${name}.${issue.path.join('.')}`, severity: 'error', message: issue.message });
        }
      }
    }
    for (const [name, token] of used) {
      const family = firstFamily(token.fontFamily);
      if (!declared.has(family.toLowerCase())) {
        findings.push({ path: `typography.${name}.fontFamily`, message: `Declare ${family} in fonts with its distribution and license metadata.` });
      }
    }
    return findings;
  },
};

function isCalendarDate(value: unknown): boolean {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = new Date(value + 'T00:00:00Z');
  return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value;
}

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
import { isRecord } from '../../model/font.js';

export const directionRecordRule: RuleDescriptor = {
  name: 'direction-record',
  severity: 'info',
  description: 'Encourages a project direction record with narrative, layout, and image guidance.',
  run(state): RuleFinding[] {
    if (state.direction === undefined) {
      return [{ path: 'direction', message: 'Record the project art direction in direction.' }];
    }
    if (!isRecord(state.direction)) {
      return [{ path: 'direction', severity: 'warning', message: 'direction must be a map of strings.' }];
    }
    const findings: RuleFinding[] = [];
    const required = ['narrative', 'layout', 'image'];
    for (const field of required) {
      const value = state.direction[field];
      if (typeof value !== 'string' || !value.trim()) {
        findings.push({ path: `direction.${field}`, severity: 'warning', message: `Record a non-empty string for direction.${field}.` });
      }
    }
    for (const [field, value] of Object.entries(state.direction)) {
      if (!required.includes(field) && typeof value !== 'string') {
        findings.push({ path: `direction.${field}`, severity: 'warning', message: 'Direction values must be strings.' });
      }
    }
    return findings;
  },
};

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
import { singleFamilyRule } from './single-family.js';
import { buildState } from './test-helpers.js';

it('reports no display/text role split only for three or more tokens all sharing a first family', () => {
  const typography = {
    title: { fontFamily: '"Lora", serif' },
    body: { fontFamily: 'lora' },
    caption: { fontFamily: "'LORA', system-ui" },
  };
  const findings = singleFamilyRule.run(buildState({ typography }));
  expect(singleFamilyRule.severity).toBe('info');
  expect(findings).toHaveLength(1);
  expect(findings[0]?.message).toContain('no display/text role split');
  expect(findings[0]?.message).toContain('fine if intentional');
  expect(singleFamilyRule.run(buildState({ typography: { title: typography.title, body: typography.body } }))).toEqual([]);
  expect(singleFamilyRule.run(buildState({ typography: { ...typography, caption: { fontFamily: 'Public Sans' } } }))).toEqual([]);
  expect(singleFamilyRule.run(buildState({ typography: { ...typography, caption: {} } }))).toEqual([]);
  expect(singleFamilyRule.run(buildState())).toEqual([]);
});


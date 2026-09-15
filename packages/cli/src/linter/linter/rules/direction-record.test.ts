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
import { directionRecordRule } from './direction-record.js';
import { buildState } from './test-helpers.js';

describe('direction-record', () => {
  it('notes a missing or empty color source in a direction record', () => {
    for (const source of [{}, { colorSource: '' }, { colorSource: ' \t ' }]) {
      expect(directionRecordRule.run(buildState({
        direction: { narrative: 'A local journal', layout: 'Columns', image: 'Documentary', ...source },
      }))).toEqual([{
        path: 'direction.colorSource',
        severity: 'info',
        message: 'Record where the color values came from: photo:<file>, catalog:<id>, brand:<guide> or reference:<url>.',
      }]);
    }
  });
  it('does not add a color source finding when a non-empty string is recorded', () => {
    for (const colorSource of ['photo:storefront.jpg', 'catalog:42', 'brand:guide.pdf', 'reference:https://example.com/palette', 'model']) {
      expect(directionRecordRule.run(buildState({
        direction: { narrative: 'A local journal', layout: 'Columns', image: 'Documentary', colorSource },
      }))).toEqual([]);
    }
  });
  it('keeps the existing warning for a non-string color source without adding info', () => {
    for (const colorSource of [null, 42, {}, [], false]) {
      expect(directionRecordRule.run(buildState({
        direction: { narrative: 'A local journal', layout: 'Columns', image: 'Documentary', colorSource },
      }))).toEqual([{
        path: 'direction.colorSource',
        severity: 'warning',
        message: 'Direction values must be strings.',
      }]);
    }
  });
  it('reports malformed maps and non-string extension values without errors or duplicate findings', () => {
    for (const direction of [null, [], false, 'editorial']) {
      expect(directionRecordRule.run(buildState({ direction }))).toEqual([expect.objectContaining({ path: 'direction', severity: 'warning' })]);
    }
    const findings = directionRecordRule.run(buildState({ direction: { narrative: 42, layout: 'Columns', image: 'Photos', custom: {}, type: false } }));
    expect(findings).toEqual([
      expect.objectContaining({ path: 'direction.narrative', severity: 'warning' }),
      expect.objectContaining({ path: 'direction.custom', severity: 'warning' }),
      expect.objectContaining({ path: 'direction.type', severity: 'warning' }),
      expect.objectContaining({ path: 'direction.colorSource', severity: 'info' }),
    ]);
  });
  it('notes an absent direction and warns for each missing or empty required field', () => {
    expect(directionRecordRule.severity).toBe('info');
    expect(directionRecordRule.run(buildState())).toEqual([expect.objectContaining({ path: 'direction' })]);
    expect(directionRecordRule.run(buildState({ direction: { narrative: ' ', layout: '', tone: 'Warm' } }))).toEqual([
      expect.objectContaining({ path: 'direction.narrative', severity: 'warning' }),
      expect.objectContaining({ path: 'direction.layout', severity: 'warning' }),
      expect.objectContaining({ path: 'direction.image', severity: 'warning' }),
      expect.objectContaining({ path: 'direction.colorSource', severity: 'info' }),
    ]);
    expect(directionRecordRule.run(buildState({ direction: { narrative: 'A local journal', layout: 'Columns', image: 'Documentary', custom: 'Free extension' } }))).toEqual([
      expect.objectContaining({ path: 'direction.colorSource', severity: 'info' }),
    ]);
  });
});

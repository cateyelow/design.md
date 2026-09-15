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

import type { RuleDescriptor } from './types.js';
import { firstFamily } from '../../model/font.js';

export const singleFamilyRule: RuleDescriptor = {
  name: 'single-family',
  severity: 'info',
  description: 'Notes typography scales of at least three tokens without a display/text family split.',
  run(state) {
    if (state.typography.size < 3) return [];
    const families = [...state.typography.values()].map(token => firstFamily(token.fontFamily).toLowerCase());
    const family = families[0];
    if (!family || !families.every(value => value === family)) return [];
    return [{
      path: 'typography',
      message: `All typography tokens use ${family}: no display/text role split; fine if intentional.`,
    }];
  },
};


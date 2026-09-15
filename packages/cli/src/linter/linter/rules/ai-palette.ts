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
import type { ResolvedColor } from '../../model/spec.js';

export const aiPaletteRule: RuleDescriptor = {
  name: 'ai-palette',
  severity: 'warning',
  description: 'Flags violet paired with cyan-blue; notes a violet primary on its own.',
  run(state) {
    // Model colors already passed through the existing CSS parser into sRGB.
    const colors = [...state.colors].map(([name, color]) => ({ name, ...toHsl(color) }));
    const eligible = colors.filter(color => color.s >= 0.45 && color.l >= 0.25 && color.l <= 0.8);
    const violet = eligible.find(color => color.h >= 250 && color.h <= 300);
    const blue = eligible.find(color => color.h >= 180 && color.h <= 235);
    if (violet && blue) {
      return [{
        path: `colors.${violet.name}`,
        message: `Violet ${violet.name} paired with cyan-blue ${blue.name} is a common generated-page palette; consider whether it supports this project's direction.`,
      }];
    }
    if (eligible.some(color => color.name === 'primary' && color.h >= 250 && color.h <= 300)) {
      return [{ path: 'colors.primary', severity: 'info', message: 'primary is violet; consider whether this familiar accent supports the project direction.' }];
    }
    return [];
  },
};

function toHsl(color: ResolvedColor): { h: number; s: number; l: number } {
  const r = color.r / 255;
  const g = color.g / 255;
  const b = color.b / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const delta = max - min;
  const l = (max + min) / 2;
  if (delta === 0) return { h: 0, s: 0, l };
  const h = max === r ? (g - b) / delta
    : max === g ? (b - r) / delta + 2 : (r - g) / delta + 4;
  return { h: (h * 60 + 360) % 360, s: delta / (1 - Math.abs(2 * l - 1)), l };
}

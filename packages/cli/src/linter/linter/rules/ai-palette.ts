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
import { isRecord } from '../../model/font.js';

export const aiPaletteRule: RuleDescriptor = {
  name: 'ai-palette',
  severity: 'warning',
  description: 'Flags violet paired with cyan-blue and off-white paper with near-black ink and at most one warm accent; notes a violet primary on its own.',
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
    const colorSource = isRecord(state.direction) ? state.direction.colorSource : undefined;
    if (typeof colorSource === 'string' && colorSource.trim() && !/^model/i.test(colorSource.trim())) {
      return [];
    }
    const labColors = [...state.colors.values()].map(toLab);
    const light = labColors.filter(color => color.l >= 88 && color.c <= 14);
    const dark = labColors.filter(color => color.l <= 25 && color.c <= 14);
    const chromatic = labColors.filter(color => color.c >= 18);
    // Each family keeps its first hue so later colors cannot shift its center.
    const families: number[] = [];
    for (const color of chromatic) {
      if (!families.some(hue => {
        const distance = Math.abs(color.h - hue);
        return Math.min(distance, 360 - distance) <= 30;
      })) {
        families.push(color.h);
      }
    }
    if (light.length > 0 && dark.length > 0 && families.length <= 1
      && (families.length === 0 || families[0]! <= 95 || families[0]! >= 345)) {
      return [{
        path: 'colors',
        severity: 'warning',
        message: "This is the palette models fall back to (off-white paper, near-black ink, at most one warm accent); take the values from the project's material or a sourced palette and record where they came from in direction.colorSource.",
      }];
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

/** Convert sRGB through D65 XYZ to CIELAB lightness, chroma, and hue. */
function toLab(color: ResolvedColor): { l: number; c: number; h: number } {
  const linearize = (channel: number): number => {
    const value = channel / 255;
    return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
  };
  const r = linearize(color.r);
  const g = linearize(color.g);
  const b = linearize(color.b);
  const delta = 6 / 29;
  const transform = (value: number): number => value > delta ** 3
    ? Math.cbrt(value) : value / (3 * delta ** 2) + 4 / 29;
  const x = transform((0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047);
  const y = transform(0.2126729 * r + 0.7151522 * g + 0.0721750 * b);
  const z = transform((0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / 1.08883);
  const a = 500 * (x - y);
  const labB = 200 * (y - z);
  return { l: 116 * y - 16, c: Math.hypot(a, labB), h: (Math.atan2(labB, a) * 180 / Math.PI + 360) % 360 };
}

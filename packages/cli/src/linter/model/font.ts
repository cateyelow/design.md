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

import { z } from 'zod';

export const FontFileSchema = z.object({
  path: z.string().min(1),
  weight: z.union([z.number().finite(), z.string()]).optional(),
  style: z.enum(['normal', 'italic']).optional(),
  format: z.enum(['woff2', 'woff', 'truetype', 'opentype']).optional(),
});

/** Font metadata shared by lint rules and the CSS font emitter. */
export const FontEntrySchema = z.object({
  family: z.string().min(1),
  source: z.string().min(1),
  license: z.string().min(1),
  webEmbedding: z.boolean(),
  licenseUrl: z.string().optional(),
  files: z.array(FontFileSchema).optional(),
  display: z.enum(['auto', 'block', 'swap', 'fallback', 'optional']).optional(),
  unicodeRange: z.string().optional(),
  fallback: z.string().optional(),
  // Calendar validity is a warning; it must not prevent CSS export.
  verified: z.unknown().optional(),
}).passthrough();

export type FontEntry = z.infer<typeof FontEntrySchema>;

/** Shared guards and family parsing for font rules and export. */
export function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

export function firstFamily(stack: string | undefined): string {
  return (stack?.split(',')[0] ?? '').trim().replace(/^['"]|['"]$/g, '').trim();
}

export const GENERIC_FAMILIES = new Set([
  'serif', 'sans-serif', 'monospace', 'cursive', 'fantasy', 'system-ui',
  'ui-serif', 'ui-sans-serif', 'ui-monospace', 'ui-rounded', 'math', 'emoji', 'fangsong',
]);

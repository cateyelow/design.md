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
import { aiPaletteRule } from './ai-palette.js';
import { buildState } from './test-helpers.js';
import { ModelHandler } from '../../model/handler.js';

describe('ai-palette', () => {
  it('warns once for off-white paper, near-black ink, and a warm accent', () => {
    for (const colors of [
      { paper: '#f2f1ec', ink: '#15150f', accent: '#a8281b' },
      { paper: '#f3efe6', ink: '#1b1a17', accent: '#ff8a4c' },
    ]) {
      const findings = aiPaletteRule.run(buildState({ colors }));
      expect(findings).toEqual([{
        path: 'colors',
        severity: 'warning',
        message: "This is the palette models fall back to (off-white paper, near-black ink, at most one warm accent); take the values from the project's material or a sourced palette and record where they came from in direction.colorSource.",
      }]);
    }
  });
  it('warns once for paper and ink without chromatic colors', () => {
    for (const colors of [
      { paper: '#f2f1ec', ink: '#15150f' },
      { paper: '#ffffff', ink: '#000000', muted: '#777777' },
    ]) {
      expect(aiPaletteRule.run(buildState({ colors }))).toEqual([
        expect.objectContaining({ path: 'colors', severity: 'warning' }),
      ]);
    }
  });
  it('skips the paper and ink warning when color values have a recorded source', () => {
    for (const colorSource of ['photo:storefront.jpg', 'catalog:42', 'brand:guide.pdf', 'reference:https://example.com/palette', '  photo:storefront.jpg  ']) {
      expect(aiPaletteRule.run(buildState({
        colors: { paper: '#f2f1ec', ink: '#15150f', accent: '#a8281b' },
        direction: { colorSource },
      }))).toEqual([]);
    }
  });
  it('keeps the existing violet findings even when a color source is recorded', () => {
    for (const colors of [
      { purple: '#8040bf', blue: '#40bfbf' },
      { primary: '#8040bf', neutral: '#777777' },
    ]) {
      const findings = aiPaletteRule.run(buildState({ colors }));
      expect(findings).toHaveLength(1);
      expect(aiPaletteRule.run(buildState({ colors, direction: { colorSource: 'photo:storefront.jpg' } }))).toEqual(findings);
    }
  });
  it('still warns for missing, malformed, empty, or model color sources', () => {
    for (const direction of [
      undefined, null, [], false, 'photo:storefront.jpg', {},
      ...['', ' \t ', 'model', 'model: chosen by hand', 'MODEL', '  MoDeL: chosen by hand  ', 42, null, {}]
        .map(colorSource => ({ colorSource })),
    ]) {
      expect(aiPaletteRule.run(buildState({
        colors: { paper: '#f2f1ec', ink: '#15150f', accent: '#a8281b' },
        direction,
      }))).toEqual([expect.objectContaining({ path: 'colors', severity: 'warning' })]);
    }
  });
  it('does not warn for two chromatic hue families, a cool accent, or a dark ground', () => {
    for (const colors of [
      { paper: '#f2f1ec', ink: '#15150f', rust: '#a8281b', teal: '#008080' },
      // This blue has a D65 Lab hue of about 280 degrees.
      { paper: '#f2f1ec', ink: '#15150f', blue: '#4477cc' },
      { background: '#171b26', text: '#c7c7c7', accent: '#ff8a4c' },
    ]) {
      expect(aiPaletteRule.run(buildState({ colors }))).toEqual([]);
    }
  });
  it('groups hues circularly within 30 degrees of the first family member', () => {
    // D65 Lab hues are approximately 5, 34, 36, 63, and 346 degrees.
    for (const accents of [
      { first: '#d3748c', second: '#d1786b' },
      { first: '#ca76a3', second: '#d3748c' },
      { first: '#d1786b', second: '#d3748c', third: '#c08352' },
    ]) {
      expect(aiPaletteRule.run(buildState({
        colors: { paper: '#f2f1ec', ink: '#15150f', ...accents },
      }))).toEqual([expect.objectContaining({ path: 'colors', severity: 'warning' })]);
    }
    for (const accents of [
      { first: '#d3748c', second: '#d07969' },
      { first: '#d3748c', second: '#d1786b', third: '#c08352' },
    ]) {
      expect(aiPaletteRule.run(buildState({
        colors: { paper: '#f2f1ec', ink: '#15150f', ...accents },
      }))).toEqual([]);
    }
  });
  it('limits warm family hues to at most 95 or at least 345 degrees', () => {
    // D65 Lab hues are approximately 94, 346, 96, and 344 degrees.
    for (const accent of ['#a29049', '#ca76a3']) {
      expect(aiPaletteRule.run(buildState({
        colors: { paper: '#f2f1ec', ink: '#15150f', accent },
      }))).toEqual([expect.objectContaining({ path: 'colors', severity: 'warning' })]);
    }
    for (const accent of ['#a09149', '#c976a5']) {
      expect(aiPaletteRule.run(buildState({
        colors: { paper: '#f2f1ec', ink: '#15150f', accent },
      }))).toEqual([]);
    }
  });
  it('requires light and dark colors within the Lab lightness and chroma limits', () => {
    for (const colors of [
      { paper: '#dfdfdf', ink: '#393939' }, // L about 89 and 24.
      { paper: '#dbe2fb', ink: '#15150f' }, // Light C about 13.
      { paper: '#f2f1ec', ink: '#293043' }, // Dark C about 13.
    ]) {
      expect(aiPaletteRule.run(buildState({ colors }))).toEqual([
        expect.objectContaining({ path: 'colors', severity: 'warning' }),
      ]);
    }
    for (const colors of [
      { paper: '#dadada', ink: '#15150f' }, // L about 87.
      { paper: '#f2f1ec', ink: '#3e3e3e' }, // L about 26.
      { paper: '#d9e2fe', ink: '#15150f' }, // Light C about 15.
      { paper: '#f2f1ec', ink: '#273046' }, // Dark C about 15.
    ]) {
      expect(aiPaletteRule.run(buildState({ colors }))).toEqual([]);
    }
  });
  it('only counts hue families for colors with Lab chroma of at least 18', () => {
    const colors = { paper: '#f2f1ec', ink: '#15150f', rust: '#a8281b' };
    // These blue-gray colors have D65 Lab chroma of about 17 and 19.
    expect(aiPaletteRule.run(buildState({ colors: { ...colors, muted: '#8690ae' } }))).toEqual([
      expect.objectContaining({ path: 'colors', severity: 'warning' }),
    ]);
    expect(aiPaletteRule.run(buildState({ colors: { ...colors, muted: '#8490b1' } }))).toEqual([]);
  });
  it('emits info for a violet primary without a cyan-blue partner', () => {
    const findings = aiPaletteRule.run(buildState({ colors: { accent: '#8040bf', primary: '#8040bf', neutral: '#777777' } }));
    expect(findings).toHaveLength(1);
    expect(findings[0]).toMatchObject({ path: 'colors.primary', severity: 'info' });
    expect(aiPaletteRule.run(buildState({ colors: { accent: '#8040bf', primary: '#777777' } }))).toEqual([]);
  });
  it('warns for violet with cyan-blue across CSS formats and ignores other palettes', () => {
    for (const colors of [
      { purple: '#8040bf', blue: '#40bfbf' },
      { purple: 'hsl(270 50% 50%)', blue: 'rgb(64, 149, 191)' },
      // These boundary hues survive the existing parser's 8-bit RGB rounding.
      { purple: 'hsl(250 100% 60%)', blue: 'hsl(235 100% 60%)' },
      { purple: 'hsl(300 100% 50%)', blue: 'hsl(180 100% 50%)' },
    ]) {
      const findings = aiPaletteRule.run(buildState({ colors }));
      expect(aiPaletteRule.severity).toBe('warning');
      expect(findings).toHaveLength(1);
      expect(findings[0]?.path).toBe('colors.purple');
      expect(findings[0]?.message).toContain('purple');
      expect(findings[0]?.message).toContain('blue');
    }
    for (const purple of ['hsl(249 50% 50%)', 'hsl(301 50% 50%)', 'hsl(270 44% 50%)', 'hsl(270 60% 24%)', 'hsl(270 60% 81%)', '#777777']) {
      expect(aiPaletteRule.run(buildState({ colors: { purple, blue: 'hsl(210 60% 50%)' } }))).toEqual([]);
    }
    const model = new ModelHandler().execute({ sourceMap: new Map(), colors: { purple: 'invalid', blue: '#0080ff' } });
    expect(aiPaletteRule.run(model.designSystem)).toEqual([]);
    expect(aiPaletteRule.run(buildState())).toEqual([]);
  });
});

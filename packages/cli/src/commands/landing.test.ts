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
import { join } from 'node:path';

const CLI = join(import.meta.dir, '../index.ts');
const FIXTURE = join(import.meta.dir, '../linter/fixtures/LANDING_FONTS.md');

function run(args: string[], stdin?: string) {
  const proc = Bun.spawnSync(['bun', 'run', CLI, ...args], {
    stdin: stdin === undefined ? 'ignore' : Buffer.from(stdin),
    stdout: 'pipe', stderr: 'pipe',
    // consola suppresses help in the test environment inherited from bun test.
    env: { ...process.env, NODE_ENV: 'production', TEST: '' },
  });
  return { code: proc.exitCode, stdout: proc.stdout.toString(), stderr: proc.stderr.toString() };
}

describe('landing CLI', () => {
  it('reports malformed landing values through lint while successful exports still exit zero', () => {
    for (const metadata of ['fonts: false\ndirection: []', 'fonts: {text: {family: 42, files: [null]}}\ndirection: {narrative: 42}', 'fonts: {text: null}\ndirection: null']) {
      const content = `---\ncolors: {primary: "#24463e"}\n${metadata}\n---\n`;
      const lint = run(['lint', '--format', 'json', '--', '-'], content);
      expect(lint.code).toBe(1);
      const findings = JSON.parse(lint.stdout).findings;
      expect(findings).toContainEqual(expect.objectContaining({ rule: 'font-license', severity: 'error' }));
      expect(findings).toContainEqual(expect.objectContaining({ rule: 'direction-record', severity: 'warning' }));
      expect(findings.some((finding: { message: string }) => finding.message.includes('Unexpected error'))).toBe(false);
      const exported = run(['export', '--format', 'css-fonts', '--', '-'], content);
      expect(exported.code).toBe(0);
      expect(exported.stderr).toBe('');
      expect(exported.stdout).toBe(':root {\n}\n');
    }
    expect(run(['export', 'definitely-missing-landing-fonts.md', '--format', 'css-fonts']).code).toBe(2);
  });
  it('advertises css-fonts and keeps the export format enum closed', () => {
    const help = run(['export', '--help']);
    expect(help.code).toBe(0);
    expect(help.stdout + help.stderr).toContain('css-fonts');
    const invalid = run(['export', 'unused.md', '--format', 'css-font']);
    expect(invalid.code).toBe(1);
    expect(JSON.parse(invalid.stderr)).toMatchObject({ error: 'INVALID_FORMAT' });
    expect(JSON.parse(invalid.stderr).message).toContain('css-fonts');
  });
  it('lints landing fonts as JSON with zero errors and exports css-fonts', () => {
    const lint = run(['lint', FIXTURE, '--format', 'json']);
    expect(lint.code).toBe(0);
    expect(JSON.parse(lint.stdout).summary.errors).toBe(0);
    const exported = run(['export', FIXTURE, '--format', 'css-fonts']);
    expect(exported.code).toBe(0);
    expect(exported.stderr).toBe('');
    expect(exported.stdout.match(/@font-face/g)).toHaveLength(2);
    expect(exported.stdout).toContain('src: url("./fonts/PublicSans-Variable.woff2") format("woff2");');
    expect(exported.stdout).toContain('font-weight: 100 900;');
    expect(exported.stdout).toContain('font-style: italic;');
    expect(exported.stdout).toContain('/* skipped reference: webEmbedding is false */');
    expect(exported.stdout).toContain('--font-text: "Public Sans", system-ui, sans-serif;');
    expect(exported.stdout).not.toContain('--font-reference');
    expect(exported.stdout).toEndWith('}\n');
    expect(exported.stdout).not.toEndWith('\n\n');
  });
});

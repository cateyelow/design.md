#!/usr/bin/env python3
"""Run the landing fork of the design.md CLI (fonts/direction rules, css-fonts export), falling back to upstream.

    python designmd.py lint DESIGN.md
    python designmd.py export --format css-fonts DESIGN.md
    python designmd.py diff OLD.md NEW.md
    python designmd.py --where

Fork lookup order: $DESIGNMD_FORK, ~/GitHub/design.md, ~/Github/design.md, C:/GitHub/design.md. The fork is
https://github.com/cateyelow/design.md (branch `landing`); set it up with
`git clone -b landing https://github.com/cateyelow/design.md && cd design.md/packages/cli && bun install`.
Without the fork this runs upstream `@google/design.md@0.4.0` through npx and says so: the fonts, direction,
generic-typeface and ai-palette rules and the css-fonts export are then unavailable.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

UPSTREAM = '@google/design.md@0.4.0'


def find_fork() -> Path | None:
    candidates = [os.environ.get('DESIGNMD_FORK'), Path.home() / 'GitHub' / 'design.md', Path.home() / 'Github' / 'design.md',
                  Path('C:/GitHub/design.md')]
    for candidate in candidates:
        if not candidate:
            continue
        cli = Path(candidate) / 'packages' / 'cli'
        # A landing rule file, not just any design.md checkout: an upstream clone would run without the landing rules.
        landing = cli / 'src' / 'linter' / 'linter' / 'rules' / 'font-license.ts'
        if (cli / 'src' / 'index.ts').is_file() and (cli / 'node_modules').is_dir() and landing.is_file():
            return Path(candidate)
    return None


def command(args: list[str]) -> tuple[list[str], str]:
    fork = find_fork()
    bun = shutil.which('bun')
    if fork and bun:
        return [bun, 'run', str(fork / 'packages' / 'cli' / 'src' / 'index.ts'), *args], f'fork {fork}'
    npx = shutil.which('npx')
    if not npx:
        raise SystemExit('Neither the fork (with bun) nor npx is available.')
    # The dot-free bin avoids the Windows .md file association opening an editor.
    return [npx, '-y', '-p', UPSTREAM, 'designmd', *args], f'upstream {UPSTREAM} (landing rules unavailable)'


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ('-h', '--help'):
        print(__doc__)
        return 0
    cmd, where = command([] if args == ['--where'] else args)
    print(f'[designmd] {where}', file=sys.stderr)
    if args == ['--where']:
        return 0
    return subprocess.run(cmd).returncode


if __name__ == '__main__':
    raise SystemExit(main())

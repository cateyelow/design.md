#!/usr/bin/env python3
"""Propose per-project art directions from curated axes and keep a ledger so sites stop looking alike.

    python direction.py propose --project "동네 빵집 예약" [--count 3] [--have photos,brand] [--round 0]
                                [--lock color="브랜드 기존 색 그대로, 새 색 금지"] [--ledger ~/.claude/design-ledger.json] [--json]
    python direction.py record --project "동네 빵집 예약" --pick pick.json [--fingerprint audit/report.json]
                               [--ledger design-ledger.json]
    python direction.py check --pick pick.json [--ledger design-ledger.json]

Candidates are reproducible for the same project name and round. A candidate passes when, against each of the
most recent ledger entries, at least `minDifferentAxes` axes differ and at least `minDifferentCore` of the core
axes (narrative, layout, image) differ, and when its reference world comes from a different group (print, places,
screens, objects) than the last `familyWindow` entries. Worlds are drawn group first, so print matter no longer wins
by sheer count. The draw only widens the options; a person or the brief chooses.

Options that need material the project lacks are never drawn: `--have photos` allows options built on the business's
own photos, `--have brand` the brand-color option; a lock always wins. `--round N` redraws from a later round.

Labels do not prove two pages look different. `record --fingerprint` stores what the browser drew (see
fingerprint.py), and `audit.py --ledger` compares the next page with it.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REFERENCES = HERE.parent / 'references'
LEDGER = Path.home() / '.claude' / 'design-ledger.json'


def load_axes(references: Path = REFERENCES) -> tuple[dict, dict]:
    directions = json.loads((references / 'directions.json').read_text(encoding='utf-8'))
    fonts = json.loads((references / 'fonts.json').read_text(encoding='utf-8'))
    pairings = {pairing['id']: pairing for pairing in fonts['pairings']}
    for axis in directions['axes']:
        if axis.get('source') == 'fonts.json#pairings':
            axis['options'] = list(pairings)
        if isinstance(axis.get('groups'), dict):
            axis['options'] = [option for options in axis['groups'].values() for option in options]
            axis['family'] = {option: group for group, options in axis['groups'].items() for option in options}
    return directions, pairings


def conflicting(pick: dict, conflicts: list) -> bool:
    return any(all(pick.get(key) == value for key, value in pair) for pair in conflicts)


def differences(pick: dict, other: dict, axes: list, core: list) -> tuple[int, int]:
    keys = [axis['key'] for axis in axes]
    return (sum(pick.get(key) != other.get(key) for key in keys),
            sum(pick.get(key) != other.get(key) for key in core))


def shared_families(pick: dict, other: dict, axes: list) -> list[str]:
    shared = []
    for axis in axes:
        family = axis.get('family') or {}
        mine = family.get(pick.get(axis['key']))
        if mine and mine == family.get(other.get(axis['key'])):
            shared.append(f'{axis["key"]}:{mine}')
    return shared


def evaluate(pick: dict, ledger: list, directions: dict) -> dict:
    rule = directions['rule']
    recent = [entry for entry in ledger if isinstance(entry.get('pick'), dict)][-rule['recent']:]
    window = rule.get('familyWindow', 0)
    worst = None
    for index, entry in enumerate(recent):
        axes_diff, core_diff = differences(pick, entry['pick'], directions['axes'], rule['core'])
        ok = axes_diff >= rule['minDifferentAxes'] and core_diff >= rule['minDifferentCore']
        row = {'project': entry.get('project'), 'differentAxes': axes_diff, 'differentCore': core_diff, 'passes': ok}
        if window and index >= len(recent) - window:
            shared = shared_families(pick, entry['pick'], directions['axes'])
            if shared:
                row['sameFamily'] = shared
                row['passes'] = ok = False
        if worst is None or (not ok and worst['passes']) or (ok == worst['passes'] and axes_diff < worst['differentAxes']):
            worst = row
    return {'passes': worst is None or worst['passes'], 'compared': len(recent), 'closest': worst}


def unavailable(directions: dict, have: set) -> set:
    return {option for need, listed in (directions.get('requires') or {}).items() if need not in have for option in listed}


def draw_option(axis: dict, rng: random.Random, excluded: frozenset = frozenset()) -> str:
    groups = axis.get('groups')
    if isinstance(groups, dict) and groups:
        usable = {name: [o for o in options if o not in excluded] for name, options in groups.items()}
        usable = {name: options for name, options in usable.items() if options}
        return rng.choice(usable[rng.choice(sorted(usable))])
    options = [option for option in axis['options'] if option not in excluded]
    return rng.choice(options or axis['options'])


def propose(project: str, count: int, locks: dict, ledger: list, directions: dict, max_rounds: int = 400,
            have: set | None = None, start: int = 0) -> list:
    unknown = [key for key in locks if key not in {axis['key'] for axis in directions['axes']}]
    if unknown:
        raise SystemExit(f'unknown axis in --lock: {", ".join(unknown)}')
    for axis in directions['axes']:
        value = locks.get(axis['key'])
        if value is None:
            continue
        if not value.strip():
            raise SystemExit(f'--lock {axis["key"]}: the value is empty')
        if value not in axis['options']:
            # A brand may already own a typeface or a layout that is not in the curated list; keep it verbatim.
            print(f'--lock {axis["key"]}: "{value}" is not a catalog option; recorded as written.', file=sys.stderr)
    excluded = frozenset(unavailable(directions, have or set()))
    seen, candidates, fallback = set(), [], []
    for round_no in range(start, start + max_rounds):
        seed = int(hashlib.sha256(f'{project}#{round_no}'.encode('utf-8')).hexdigest()[:16], 16)
        rng = random.Random(seed)
        pick = {axis['key']: locks.get(axis['key']) or draw_option(axis, rng, excluded) for axis in directions['axes']}
        key = json.dumps(pick, ensure_ascii=False, sort_keys=True)
        if key in seen or conflicting(pick, directions['conflicts']):
            continue
        seen.add(key)
        verdict = evaluate(pick, ledger, directions)
        row = {'round': round_no, 'pick': pick, 'ledger': verdict}
        (candidates if verdict['passes'] else fallback).append(row)
        if len(candidates) >= count:
            break
    return candidates + fallback[:max(0, count - len(candidates))]


def read_ledger(path: Path) -> list:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding='utf-8'))
    return data.get('entries', []) if isinstance(data, dict) else data


def write_ledger(path: Path, entries: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps({'version': 1, 'entries': entries}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def render(project: str, rows: list, directions: dict, pairings: dict) -> str:
    labels = {axis['key']: axis['label'] for axis in directions['axes']}
    out = [f'# 디렉션 후보: {project}', '']
    for index, row in enumerate(rows, 1):
        verdict = row['ledger']
        closest = verdict['closest']
        status = '원장 기준 통과' if verdict['passes'] else '원장 기준 미달'
        if closest:
            status += f' (가장 가까운 기록 「{closest["project"]}」: 다른 축 {closest["differentAxes"]}개, 핵심 축 {closest["differentCore"]}개'
            if closest.get('sameFamily'):
                status += f', 같은 계열 {", ".join(closest["sameFamily"])}'
            status += ')'
        out += [f'## 후보 {index} (round {row["round"]}): {status}', '']
        for key, value in row['pick'].items():
            shown = value
            if key == 'type' and value in pairings:
                pairing = pairings[value]
                shown = f'{pairing["label"]} (`{value}`)'
            out.append(f'- {labels[key]}: {shown}')
        prompt = directions['imagePrompts'].get(row['pick']['image'])
        recipes = next((axis.get('recipes') or {} for axis in directions['axes'] if axis['key'] == 'color'), {})
        recipe = recipes.get(row['pick']['color'])
        out += ['', f'이미지 프롬프트 핵심: {prompt or "이미지 생성 없음"}']
        if recipe:
            out.append(f'색 가져오기: {recipe}')
        out.append('')
    return '\n'.join(out)


def parse_locks(values: list) -> dict:
    locks = {}
    for value in values or []:
        if '=' not in value:
            raise SystemExit(f'--lock expects axis=value, got "{value}"')
        key, _, option = value.partition('=')
        locks[key.strip()] = option.strip()
    return locks


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    p_propose = sub.add_parser('propose')
    p_propose.add_argument('--project', required=True)
    p_propose.add_argument('--count', type=int, default=3)
    p_propose.add_argument('--lock', action='append', help='axis=value fixed by the brand or brief')
    p_propose.add_argument('--ledger', type=Path, default=LEDGER)
    p_propose.add_argument('--have', default='', help='material the project has: photos, brand (comma-separated)')
    p_propose.add_argument('--round', type=int, default=0, help='start drawing from this round (redraw)')
    p_propose.add_argument('--json', action='store_true')
    p_record = sub.add_parser('record')
    p_record.add_argument('--project', required=True)
    p_record.add_argument('--pick', type=Path, required=True, help='JSON file with the chosen axis values')
    p_record.add_argument('--ledger', type=Path, default=LEDGER)
    p_record.add_argument('--note', default='')
    p_record.add_argument('--fingerprint', type=Path,
                          help='audit.py report.json or fingerprint.py --json output for the finished page')
    p_check = sub.add_parser('check')
    p_check.add_argument('--pick', type=Path, required=True)
    p_check.add_argument('--ledger', type=Path, default=LEDGER)
    args = parser.parse_args(argv)

    directions, pairings = load_axes()
    if args.command == 'propose':
        have = {item.strip() for item in args.have.split(',') if item.strip()}
        unknown = have - set(directions.get('requires') or {})
        if unknown:
            raise SystemExit(f'--have: unknown material {", ".join(sorted(unknown))}; use {", ".join(directions["requires"])}')
        rows = propose(args.project, max(1, args.count), parse_locks(args.lock), read_ledger(args.ledger.expanduser()),
                       directions, have=have, start=max(0, args.round))
        if args.json:
            print(json.dumps({'project': args.project, 'candidates': rows}, ensure_ascii=False, indent=2))
        else:
            print(render(args.project, rows, directions, pairings))
        return 0

    pick = json.loads(args.pick.read_text(encoding='utf-8'))
    pick = pick.get('pick', pick)
    missing = [axis['key'] for axis in directions['axes']
               if not isinstance(pick.get(axis['key']), str) or not pick[axis['key']].strip()]
    if missing:
        print(f'pick needs a non-empty value for: {", ".join(missing)}', file=sys.stderr)
        return 2
    args.ledger = args.ledger.expanduser()
    ledger = read_ledger(args.ledger)
    verdict = evaluate(pick, ledger, directions)
    if args.command == 'check':
        print(json.dumps(verdict, ensure_ascii=False, indent=2))
        return 0 if verdict['passes'] else 1
    entry = {'project': args.project, 'recorded': dt.date.today().isoformat(), 'pick': pick,
             'passes': verdict['passes'], 'note': args.note}
    if args.fingerprint:
        measured = json.loads(args.fingerprint.read_text(encoding='utf-8'))
        measured = measured.get('fingerprint', measured) if isinstance(measured, dict) else None
        if not isinstance(measured, dict) or 'ground' not in measured:
            print(f'{args.fingerprint}: no fingerprint found (run audit.py on the finished page first)', file=sys.stderr)
            return 2
        entry['fingerprint'] = measured
    ledger.append(entry)
    write_ledger(args.ledger, ledger)
    print(json.dumps({'recorded': args.project, 'ledger': str(args.ledger), 'check': verdict}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

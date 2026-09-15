#!/usr/bin/env python3
"""Take color values from outside the model: photos of the business, a published color dictionary, or the brand.

    python palette.py extract photo.jpg [more.jpg ...] [--count 6] [--json]
    python palette.py wada --draw 3 --project "동네 빵집" [--json]      # or --combo 214
    python palette.py roles --colors "#f9c1ce,#cab356,#2d3b2d" --source "catalog:wada#214" [--scheme light|dark|ground]

Asked for a palette, a model returns the same cream paper, warm black and one rust accent on every project, even
when the direction labels differ. `extract` measures real photos. `wada` draws combinations from Sanzo Wada's
A Dictionary of Colour Combinations (348 combinations of 159 colors, 1933 to 1934), digitized by
mattdesl/dictionary-of-colour-combinations. The file is downloaded at a pinned commit and cached rather than bundled,
because that repository states a license for its code but not for the data. `roles` turns a handful of sourced colors
into DESIGN.md tokens. It moves only lightness, and chroma when a color leaves the sRGB gamut, until text contrast
holds, and prints each move so the source stays traceable. Record the printed `colorSource` in DESIGN.md `direction`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fingerprint import delta_e, group_colors, lab  # noqa: E402

WADA_COMMIT = 'c142bd0bc8049ea48db4da5eb397981f047e8ef4'
WADA_URL = f'https://raw.githubusercontent.com/mattdesl/dictionary-of-colour-combinations/{WADA_COMMIT}/colors.json'
WADA_SHA256 = '555f11c32eb8133078fd470dd7d5320533aaa8b636f12fa06a8dd3d0ee2703b4'
CACHE = Path(os.environ.get('DESIGN_MD_CACHE', Path.home() / '.cache' / 'design-md'))


# ------------------------------------------------------------------ color math

def lab_to_rgb(lightness: float, a: float, b: float) -> tuple[float, float, float]:
    fy = (lightness + 16) / 116
    fx, fz = fy + a / 500, fy - b / 200

    def inverse(t):
        return t ** 3 if t ** 3 > 216 / 24389 else (116 * t - 16) / (24389 / 27)

    x, y, z = inverse(fx) * 0.95047, inverse(fy), inverse(fz) * 1.08883
    linear = (3.2406 * x - 1.5372 * y - 0.4986 * z, -0.9689 * x + 1.8758 * y + 0.0415 * z,
              0.0557 * x - 0.2040 * y + 1.0570 * z)

    def gamma(c):
        return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055

    return tuple(gamma(channel) * 255 for channel in linear)


def in_gamut(rgb) -> bool:
    return all(-0.5 <= channel <= 255.5 for channel in rgb)


def from_lab(lightness: float, a: float, b: float) -> dict:
    """Nearest in-gamut color at this lightness and hue, reducing chroma only when needed."""
    lightness = max(0.0, min(100.0, lightness))
    scale = 1.0
    rgb = lab_to_rgb(lightness, a, b)
    while not in_gamut(rgb) and scale > 0:
        scale = round(scale - 0.02, 2)
        rgb = lab_to_rgb(lightness, a * scale, b * scale)
    return lab(tuple(max(0, min(255, round(channel))) for channel in rgb))


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip('#')
    if len(value) == 3:
        value = ''.join(ch * 2 for ch in value)
    if len(value) != 6 or any(ch not in '0123456789abcdefABCDEF' for ch in value):
        raise ValueError(f'not a #RRGGBB color: {value!r}')
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def luminance(color: dict) -> float:
    def channel(value):
        value /= 255
        return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(v) for v in hex_to_rgb(color['hex']))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(one: dict, two: dict) -> float:
    high, low = sorted((luminance(one), luminance(two)), reverse=True)
    return round((high + 0.05) / (low + 0.05), 2)


def push_lightness(color: dict, against: dict, target: float) -> dict:
    """Move lightness away from `against` until the contrast target holds or lightness runs out."""
    step = -1 if luminance(color) <= luminance(against) else 1
    current = color
    while contrast(current, against) < target and 0 < current['L'] < 100:
        current = from_lab(current['L'] + step, color['a'], color['b'])
    return current


# ------------------------------------------------------------------ sources

def extract(paths: list[Path], count: int = 6) -> list[dict]:
    from PIL import Image

    weighted = []
    for path in paths:
        with Image.open(path) as source:
            image = source.convert('RGB')
        image.thumbnail((360, 360))
        quantized = image.quantize(colors=32, method=Image.Quantize.MEDIANCUT)
        palette = quantized.getpalette()
        total = image.width * image.height * len(paths)
        weighted += [(lab(palette[index * 3:index * 3 + 3]), found / total)
                     for found, index in quantized.getcolors(maxcolors=256)]
    groups = group_colors(weighted, 10.0)
    # Keep the large neutrals and the colors that carry hue, not just the biggest areas.
    chosen = groups[:max(2, count // 2)]
    for group in sorted(groups[len(chosen):], key=lambda item: -item['C'] * math.sqrt(item['share'])):
        if len(chosen) >= count:
            break
        if group['share'] >= 0.004 and all(delta_e(group, other) >= 18 for other in chosen):
            chosen.append(group)
    names = ','.join(path.name for path in paths)
    return [{**color, 'share': round(color['share'], 4), 'source': f'photo:{names}#{index}'}
            for index, color in enumerate(chosen, 1)]


def wada_catalog(refresh: bool = False) -> list[dict]:
    path = CACHE / f'wada-{WADA_COMMIT[:12]}.json'
    if refresh or not path.exists():
        with urllib.request.urlopen(WADA_URL, timeout=60) as response:
            body = response.read()
        if hashlib.sha256(body).hexdigest() != WADA_SHA256:
            raise SystemExit(f'{WADA_URL}: SHA-256 does not match the pinned file; not caching it')
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix('.tmp')
        tmp.write_bytes(body)
        tmp.replace(path)
    body = path.read_bytes()
    if hashlib.sha256(body).hexdigest() != WADA_SHA256:
        raise SystemExit(f'{path}: cached file changed since it was verified; run with --refresh')
    colors = json.loads(body)
    if not isinstance(colors, list) or not all('hex' in item and 'combinations' in item for item in colors):
        raise SystemExit(f'{path}: not the expected colors.json shape; delete it and run again')
    return colors


def wada_combinations(colors: list[dict]) -> dict[int, list[dict]]:
    combos: dict[int, list[dict]] = {}
    for color in colors:
        for number in color['combinations']:
            combos.setdefault(number, []).append({'name': color['name'], 'hex': color['hex']})
    return dict(sorted(combos.items()))


def draw(combos: dict[int, list[dict]], project: str, count: int) -> list[int]:
    seed = int(hashlib.sha256(f'wada#{project}'.encode('utf-8')).hexdigest()[:16], 16)
    usable = [number for number, items in combos.items() if len(items) >= 3]
    return random.Random(seed).sample(usable, min(count, len(usable)))


# ------------------------------------------------------------------ roles

def roles(colors: list[dict], scheme: str, source: str) -> dict:
    if len(colors) < 2:
        raise SystemExit('roles needs at least two colors')
    pool = list(colors)
    moves = []

    def take(color):
        pool.remove(color)
        return color

    if scheme == 'light':
        ground = take(max(pool, key=lambda c: c['L']))
        if ground['L'] < 70:
            moved = from_lab(70, ground['a'], ground['b'])
            moves.append({'role': 'ground', 'from': ground['hex'], 'to': moved['hex'], 'reason': 'light scheme needs L >= 70'})
            ground = moved
        ink = take(min(pool, key=lambda c: c['L']))
    elif scheme == 'dark':
        ground = take(min(pool, key=lambda c: c['L']))
        if ground['L'] > 25:
            moved = from_lab(25, ground['a'], ground['b'])
            moves.append({'role': 'ground', 'from': ground['hex'], 'to': moved['hex'], 'reason': 'dark scheme needs L <= 25'})
            ground = moved
        ink = take(max(pool, key=lambda c: c['L']))
    elif scheme == 'ground':
        ground = take(max(pool, key=lambda c: c['C']))
        ink = take(max(pool, key=lambda c: abs(luminance(c) - luminance(ground))))
    else:
        raise SystemExit(f'unknown scheme: {scheme}')

    fixed = push_lightness(ink, ground, 7.0)
    if contrast(fixed, ground) < 4.5:
        # The ink's own hue cannot reach body contrast on this ground; fall back to the lightness extreme.
        fixed = from_lab(0 if luminance(ground) > 0.18 else 100, 0, 0)
    if fixed['hex'] != ink['hex']:
        moves.append({'role': 'ink', 'from': ink['hex'], 'to': fixed['hex'],
                      'reason': f'body text contrast {contrast(fixed, ground)}:1 on the ground'})
    ink = fixed

    tokens = {'ground': ground, 'ink': ink}
    if pool:
        accent = take(max(pool, key=lambda c: c['C']))
        fixed = push_lightness(accent, ground, 3.0)
        if fixed['hex'] != accent['hex']:
            moves.append({'role': 'accent', 'from': accent['hex'], 'to': fixed['hex'],
                          'reason': f'large text and UI contrast {contrast(fixed, ground)}:1 on the ground'})
        tokens['accent'] = fixed
    if pool:
        tokens['second'] = pool[0]

    ratios = {f'{role}/ground': contrast(color, ground) for role, color in tokens.items() if role != 'ground'}
    return {'colorSource': source, 'scheme': scheme,
            'tokens': {role: color['hex'] for role, color in tokens.items()},
            'moves': moves, 'contrast': ratios}


def design_snippet(result: dict) -> str:
    tokens = result['tokens']
    lines = ['colors:', f'  primary: "{tokens.get("accent", tokens["ink"])}"']
    lines += [f'  {role}: "{value}"' for role, value in tokens.items()]
    lines += ['direction:', f'  colorSource: "{result["colorSource"]} ({result["scheme"]} scheme)"']
    return '\n'.join(lines)


# ------------------------------------------------------------------ cli

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    p_extract = sub.add_parser('extract')
    p_extract.add_argument('images', nargs='+', type=Path)
    p_extract.add_argument('--count', type=int, default=6)
    p_extract.add_argument('--json', action='store_true')
    p_wada = sub.add_parser('wada')
    p_wada.add_argument('--combo', type=int, action='append')
    p_wada.add_argument('--draw', type=int, default=0)
    p_wada.add_argument('--project', default='')
    p_wada.add_argument('--refresh', action='store_true')
    p_wada.add_argument('--json', action='store_true')
    p_roles = sub.add_parser('roles')
    p_roles.add_argument('--colors', required=True, help='comma-separated #RRGGBB values from one source')
    p_roles.add_argument('--source', required=True, help='photo:<file>, catalog:wada#<n>, brand:<guide> or reference:<url>')
    p_roles.add_argument('--scheme', choices=('light', 'dark', 'ground'), default='light')
    p_roles.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)

    if args.command == 'extract':
        missing = [str(path) for path in args.images if not path.is_file()]
        if missing:
            print(f'not found: {", ".join(missing)}', file=sys.stderr)
            return 2
        swatches = extract(args.images, max(2, args.count))
        if args.json:
            print(json.dumps(swatches, ensure_ascii=False, indent=2))
        else:
            for item in swatches:
                print(f"{item['hex']}  L{item['L']:5.1f} C{item['C']:5.1f} h{item['h']:5.1f}  area {item['share']:.3f}  {item['source']}")
            print(f"\nroles --colors \"{','.join(item['hex'] for item in swatches)}\" --source \"photo:{','.join(p.name for p in args.images)}\"")
        return 0

    if args.command == 'wada':
        if not args.combo and not args.draw:
            parser.error('wada needs --combo N or --draw N --project NAME')
        if args.draw and not args.project.strip():
            parser.error('--draw needs --project so the draw is reproducible per project')
        combos = wada_combinations(wada_catalog(args.refresh))
        numbers = list(args.combo or []) + (draw(combos, args.project, args.draw) if args.draw else [])
        unknown = [number for number in numbers if number not in combos]
        if unknown:
            print(f'no such combination: {unknown} (1 to {max(combos)})', file=sys.stderr)
            return 2
        rows = [{'combination': number, 'colors': combos[number], 'source': f'catalog:wada#{number}'} for number in numbers]
        if args.json:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            for row in rows:
                swatch = '  '.join(f"{item['hex']} {item['name']}" for item in row['colors'])
                print(f"#{row['combination']:<4} {swatch}")
                print(f"      roles --colors \"{','.join(item['hex'] for item in row['colors'])}\" --source \"{row['source']}\"")
        return 0

    try:
        colors = [lab(hex_to_rgb(value)) for value in args.colors.split(',') if value.strip()]
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2
    result = roles(colors, args.scheme, args.source)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(design_snippet(result))
        for move in result['moves']:
            print(f"# moved {move['role']} {move['from']} -> {move['to']}: {move['reason']}")
        print('# contrast ' + ', '.join(f'{key} {value}:1' for key, value in result['contrast'].items()))
    return 0


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())

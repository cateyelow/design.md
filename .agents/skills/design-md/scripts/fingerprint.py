#!/usr/bin/env python3
"""Measure how a rendered page looks, so pages can be compared with each other and with known generated looks.

    python fingerprint.py http://127.0.0.1:8000/ [--width 1440] [--ledger ~/.claude/design-ledger.json] [--json]

The direction labels in DESIGN.md say what was intended; two pages with different labels can still come out as the
same cream paper, warm black ink and one rust accent. This measures what the browser drew instead: ground, ink and
accent colors (pixels with photos hidden, and text weighted by character count), the type scale, and decoration
habits such as hairline rules, small letter-spaced labels, numbered headings, decorative monospace, pills, shadows
and gradients. `audit.py` runs the same measurement at its widest width and reports `generated-look` and
`near-recent`; `direction.py record --fingerprint` stores it in the ledger.
"""
from __future__ import annotations

import argparse
import io
import json
import math
import re
import sys
from pathlib import Path

MEASURE_JS = r"""() => {
    const shown = new Map();
    const isShown = el => {
        if (!shown.has(el)) {
            const ok = !el.closest('script, style, noscript, template, head') &&
                (!el.checkVisibility || el.checkVisibility({opacityProperty: true, visibilityProperty: true}));
            shown.set(el, ok);
        }
        return shown.get(el);
    };
    const firstFamily = value => {
        const match = value.match(/^\s*(?:"([^"]+)"|'([^']+)'|([^,]+))/);
        return match ? (match[1] || match[2] || match[3]).trim() : '';
    };
    const ownText = el => [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.nodeValue).join('').replace(/\s+/g, '');
    const mono = /mono|courier|consolas|menlo|monaco|cascadia|source code|fira code|jetbrains/i;
    const textColors = {}, families = {}, sizes = {};
    let chars = 0, monoDecor = 0;
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
        const text = node.nodeValue.replace(/\s+/g, '');
        const el = node.parentElement;
        if (!text || !el || !isShown(el)) continue;
        const css = getComputedStyle(el), n = text.length;
        chars += n;
        textColors[css.color] = (textColors[css.color] || 0) + n;
        const family = firstFamily(css.fontFamily);
        families[family] = (families[family] || 0) + n;
        const size = Math.round(parseFloat(css.fontSize) * 2) / 2;
        sizes[size] = (sizes[size] || 0) + n;
        if (mono.test(css.fontFamily) && !el.closest('pre, code, kbd, samp')) monoDecor += n;
    }
    const doc = document.documentElement;
    const pageWidth = Math.max(1, doc.scrollWidth), pageHeight = Math.max(1, doc.scrollHeight);
    let hairlines = 0, trackedSmall = 0, uppercase = 0, shadows = 0, gradients = 0, pills = 0;
    let boxes = 0, rounded = 0, imageArea = 0, iconTiles = 0, cards = 0;
    const transparent = c => c === 'transparent' || /rgba\([^)]*,\s*0\)$/.test(c);
    const framed = css => ['Top', 'Right', 'Bottom', 'Left'].every(side =>
        css[`border${side}Style`] !== 'none' && (parseFloat(css[`border${side}Width`]) || 0) > 0);
    const heading = 'h1, h2, h3, h4';
    for (const el of document.body.querySelectorAll('*')) {
        if (!isShown(el)) continue;
        const r = el.getBoundingClientRect();
        if (r.width < 1 || r.height < 1) continue;
        const css = getComputedStyle(el);
        const widths = ['Top', 'Right', 'Bottom', 'Left'].filter(side => css[`border${side}Style`] !== 'none')
            .map(side => parseFloat(css[`border${side}Width`]) || 0).filter(w => w > 0);
        if (widths.some(w => w <= 1.5)) hairlines++;
        const text = ownText(el);
        if (text) {
            const size = parseFloat(css.fontSize) || 16;
            const spacing = parseFloat(css.letterSpacing) || 0;
            if (size <= 14 && spacing / size >= 0.04) trackedSmall++;
            if (css.textTransform === 'uppercase') uppercase++;
        }
        if (css.boxShadow && css.boxShadow !== 'none') shadows++;
        const bg = css.backgroundImage || '';
        if (/gradient/.test(bg)) gradients++;
        const painted = !transparent(css.backgroundColor) || widths.length > 0;
        const radius = parseFloat(css.borderTopLeftRadius) || 0;
        if (painted && r.width >= 40 && r.height >= 40) {
            boxes++;
            if (radius >= 8) rounded++;
        }
        if (painted && r.height <= 44 && r.width < 420 && radius >= r.height / 2 - 1 && text) pills++;
        // A small icon in its own painted square next to or inside a heading, repeated down the page. The square
        // is either the icon's parent or the svg itself with a background (measured on a generated page).
        if (el.matches('svg, img') && r.width <= 72 && r.height <= 72) {
            const own = !transparent(css.backgroundColor) || framed(css);
            const tile = own ? el : el.parentElement;
            if (tile && tile !== document.body) {
                const tileBox = tile.getBoundingClientRect(), tileCss = getComputedStyle(tile);
                const painted = own || (r.width <= 40 && (!transparent(tileCss.backgroundColor) || framed(tileCss)));
                const beside = tile.closest(heading) ||
                    [...(tile.parentElement ? tile.parentElement.children : [])].some(k => k !== tile && k.matches(heading));
                if (painted && beside && tileBox.width <= 72 && tileBox.height <= 72) iconTiles++;
            }
        }
        // A grid or wrapping row whose children are boxes, each painted or framed: the card grid.
        if (css.display === 'grid' || css.display === 'inline-grid' || (css.display === 'flex' && css.flexWrap === 'wrap')) {
            const boxed = [...el.children].filter(kid => {
                if (!isShown(kid)) return false;
                const kidBox = kid.getBoundingClientRect(), kidCss = getComputedStyle(kid);
                const painted = !transparent(kidCss.backgroundColor) && kidCss.backgroundColor !== css.backgroundColor;
                return (painted || framed(kidCss)) && kidBox.width >= 160 && kidBox.height >= 120;
            });
            if (boxed.length >= 3) cards += boxed.length;
        }
        const media = el.matches('img, picture, video, canvas, iframe, object, embed') ||
            (el.matches('svg') && r.width * r.height >= 10000) || /url\(/.test(bg);
        if (media && !el.closest('picture:not(:scope)')) imageArea += r.width * r.height;
    }
    const headings = [...document.querySelectorAll('h1, h2, h3, h4')].filter(isShown);
    const numbered = headings.filter(h => /^\s*(?:\d{1,2}(?:[.)]|\s|$)|0\d|[IVX]{1,4}\.|§)/.test(h.innerText)).length;
    const h1 = headings.find(h => h.matches('h1'));
    return {
        chars, textColors, families, sizes, monoDecor,
        display: h1 ? firstFamily(getComputedStyle(h1).fontFamily) : '',
        pageWidth, pageHeight, hairlines, trackedSmall, uppercase, shadows, gradients, pills, boxes, rounded,
        imageArea, iconTiles, cards, headings: headings.length, numbered,
        captions: document.querySelectorAll('figcaption').length + document.querySelectorAll('sup').length,
    };
}"""

# Photos say little about the page's own palette and would swamp it, so they are hidden for the pixel pass.
HIDE_MEDIA_JS = r"""() => {
    const style = document.createElement('style');
    style.id = '__fingerprint_hide';
    style.textContent = 'img,picture,video,canvas,iframe,object,embed{visibility:hidden!important}' +
        '[data-fingerprint-hide]{background-image:none!important}';
    document.head.appendChild(style);
    for (const el of document.querySelectorAll('*')) {
        if (/url\(/.test(getComputedStyle(el).backgroundImage)) el.setAttribute('data-fingerprint-hide', '');
    }
}"""
RESTORE_MEDIA_JS = r"""() => {
    document.getElementById('__fingerprint_hide')?.remove();
    for (const el of document.querySelectorAll('[data-fingerprint-hide]')) el.removeAttribute('data-fingerprint-hide');
}"""

CHROMATIC = 18.0        # Lab chroma above which a color reads as a color rather than a tinted neutral
PALETTE_GROUND = 12.0   # delta E between grounds below which two pages share a ground
PALETTE_INK = 25.0     # near-black and dark grey text read as the same ink
PALETTE_ACCENT = 20.0
RESTRAINED = 0.06       # chromatic pixel share under which a page is "neutrals plus a spot"


# ------------------------------------------------------------------ color

def parse_css_color(value: str) -> tuple[float, float, float] | None:
    match = re.match(r'rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)', value or '')
    if match:
        return tuple(float(part) for part in match.groups())
    match = re.match(r'color\(srgb\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)', value or '')
    if match:
        return tuple(float(part) * 255 for part in match.groups())
    return None


def lab(rgb) -> dict:
    def linear(channel):
        channel /= 255
        return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4

    r, g, b = (linear(float(value)) for value in rgb[:3])
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883

    def f(t):
        return t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116

    fx, fy, fz = f(x), f(y), f(z)
    lightness, a, b_ = 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)
    hexcode = '#' + ''.join(f'{max(0, min(255, round(float(v)))):02x}' for v in rgb[:3])
    return {'hex': hexcode, 'L': round(lightness, 2), 'a': round(a, 2), 'b': round(b_, 2),
            'C': round(math.hypot(a, b_), 2), 'h': round(math.degrees(math.atan2(b_, a)) % 360, 1)}


def delta_e(one: dict, two: dict) -> float:
    return math.dist((one['L'], one['a'], one['b']), (two['L'], two['a'], two['b']))


def hue_gap(one: float, two: float) -> float:
    gap = abs(one - two) % 360
    return min(gap, 360 - gap)


def group_colors(weighted: list[tuple[dict, float]], radius: float) -> list[dict]:
    """Merge colors closer than `radius` (delta E), heaviest first; each group keeps its heaviest member."""
    groups: list[dict] = []
    for color, weight in sorted(weighted, key=lambda item: -item[1]):
        for group in groups:
            if delta_e(group, color) < radius:
                group['share'] += weight
                break
        else:
            groups.append({**color, 'share': weight})
    return sorted(groups, key=lambda group: -group['share'])


def pixel_palette(png: bytes, colors: int = 24) -> list[dict]:
    from PIL import Image

    with Image.open(io.BytesIO(png)) as source:
        image = source.convert('RGB')
    factor = max(1, image.width // 480)
    if factor > 1:
        image = image.reduce(factor)
    quantized = image.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
    palette = quantized.getpalette()
    total = image.width * image.height
    weighted = [(lab(palette[index * 3:index * 3 + 3]), count / total)
                for count, index in quantized.getcolors(maxcolors=256)]
    return group_colors(weighted, 6.0)


# ------------------------------------------------------------------ features

def summarize(raw: dict, swatches: list[dict]) -> dict:
    chars = max(1, raw['chars'])
    text = [(lab(rgb), count / chars) for value, count in raw['textColors'].items()
            if (rgb := parse_css_color(value)) is not None]
    text_groups = group_colors(text, 8.0)
    ground = swatches[0] if swatches else lab((255, 255, 255)) | {'share': 1.0}
    # The ink is the body text color that stands off the ground, not simply the most frequent text color: a page
    # with ground-colored text on light panels would otherwise report ink == ground (measured on a maroon page).
    readable = [color for color in text_groups if color['share'] >= 0.1]
    ink = (max(readable, key=lambda color: abs(color['L'] - ground['L'])) if readable
           else text_groups[0] if text_groups else lab((0, 0, 0)) | {'share': 1.0})

    accents: list[dict] = []

    def is_base(color):
        return delta_e(color, ground) < 10 or delta_e(color, ink) < 10

    for swatch in swatches:
        if swatch['C'] >= CHROMATIC and swatch['share'] >= 0.002 and not is_base(swatch):
            accents.append({**swatch, 'pixelShare': round(swatch['share'], 4), 'textShare': 0.0})
    for color in text_groups:
        if color['C'] < CHROMATIC or color['share'] < 0.01 or is_base(color):
            continue
        match = next((item for item in accents if delta_e(item, color) < 15), None)
        if match:
            match['textShare'] = round(match['textShare'] + color['share'], 4)
        else:
            accents.append({**color, 'pixelShare': 0.0, 'textShare': round(color['share'], 4)})
    for item in accents:
        item.pop('share', None)
    accents.sort(key=lambda item: -(item['pixelShare'] + item['textShare']))

    hues: list[float] = []
    for item in accents:
        if all(hue_gap(item['h'], hue) >= 30 for hue in hues):
            hues.append(item['h'])

    sizes = sorted((float(size), count) for size, count in raw['sizes'].items())
    running, body = 0, 16.0
    for size, count in sizes:
        running += count
        if running >= chars / 2:
            body = size
            break
    largest = max((size for size, count in sizes if count >= 2), default=body)
    families = sorted(raw['families'].items(), key=lambda item: -item[1])[:3]
    per_1000 = 1000 / max(1, raw['pageHeight'])

    return {
        'ground': {key: ground[key] for key in ('hex', 'L', 'a', 'b', 'C', 'h')} | {'share': round(ground['share'], 3)},
        'ink': {key: ink[key] for key in ('hex', 'L', 'a', 'b', 'C', 'h')} | {'share': round(ink['share'], 3)},
        'accents': accents[:6],
        'accentHues': hues,
        'chromaticShare': round(sum(s['share'] for s in swatches if s['C'] >= CHROMATIC), 4),
        'darkGround': ground['L'] < 30,
        'bodySize': body,
        'largestSize': largest,
        'scale': round(largest / max(body, 1), 2),
        'display': raw['display'],
        'families': [[name, round(count / chars, 3)] for name, count in families],
        'trackedSmall': raw['trackedSmall'],
        'uppercase': raw['uppercase'],
        'headings': raw['headings'],
        'numberedHeadings': round(raw['numbered'] / raw['headings'], 2) if raw['headings'] else 0.0,
        'monoDecor': round(raw['monoDecor'] / chars, 3),
        'hairlinesPer1000': round(raw['hairlines'] * per_1000, 2),
        'pills': raw['pills'],
        'roundedShare': round(raw['rounded'] / raw['boxes'], 2) if raw['boxes'] else 0.0,
        'shadows': raw['shadows'],
        'gradients': raw['gradients'],
        'captions': raw['captions'],
        'imageShare': round(min(1.0, raw['imageArea'] / (raw['pageWidth'] * raw['pageHeight'])), 3),
        'iconTiles': raw.get('iconTiles', 0),
        'cardGrid': raw.get('cards', 0),
        'pageHeight': raw['pageHeight'],
        'textChars': raw['chars'],
    }


def measure(page, timeout: float = 30) -> dict:
    """Measure a loaded Playwright page. Leaves the page as it found it."""
    raw = page.evaluate(MEASURE_JS)
    page.evaluate(HIDE_MEDIA_JS)
    try:
        png = page.screenshot(full_page=True, timeout=timeout * 1000)
    finally:
        page.evaluate(RESTORE_MEDIA_JS)
    fingerprint = summarize(raw, pixel_palette(png))
    fingerprint['width'] = page.viewport_size['width'] if page.viewport_size else None
    return fingerprint


# ------------------------------------------------------------------ judgments

def tics(fp: dict) -> list[str]:
    get = fp.get
    found = {
        'hairline rules as the main structure': get('hairlinesPer1000', 0) >= 4,
        'small letter-spaced labels': get('trackedSmall', 0) >= 3,
        'numbered section headings': get('headings', 0) >= 3 and get('numberedHeadings', 0) >= 0.5,
        'monospace used as decoration': get('monoDecor', 0) >= 0.02,
        'figure captions and footnote marks': get('captions', 0) >= 2,
        'uppercase labels': get('uppercase', 0) >= 3,
        'icon tiles beside headings': get('iconTiles', 0) >= 3,
        'boxed card grid': get('cardGrid', 0) >= 4,
    }
    return [name for name, hit in found.items() if hit]


EDITORIAL = {'hairline rules as the main structure', 'small letter-spaced labels', 'numbered section headings',
             'monospace used as decoration', 'figure captions and footnote marks', 'uppercase labels'}
DEVTOOL = {'monospace used as decoration', 'small letter-spaced labels', 'uppercase labels'}


def generated_looks(fp: dict) -> list[dict]:
    """Looks a model reaches for when nothing outside it decides. Each needs its color condition and habits."""
    looks = []
    ground, ink, hues = fp['ground'], fp['ink'], fp['accentHues']
    habits = [habit for habit in tics(fp) if habit in EDITORIAL]
    restrained = fp['chromaticShare'] <= RESTRAINED and len(hues) <= 1
    # A tinted, warm paper rather than plain white: plain white with black type is every browser's default and
    # plenty of human editorial work (measured: kinfolk.com), so it is not evidence on its own.
    paper = 86 <= ground['L'] <= 98.5 and 1.5 <= ground['C'] <= 14 and 50 <= ground['h'] <= 115
    if (paper and ink['L'] <= 25 and restrained
            and (not hues or hues[0] <= 95 or hues[0] >= 345) and len(habits) >= 2):
        looks.append({'id': 'paper-ink-accent',
                      'label': 'off-white paper, near-black ink, at most one warm accent, editorial habits',
                      'evidence': {'ground': ground['hex'], 'ink': ink['hex'], 'accentHues': hues, 'habits': habits}})
    # Dark product pages with rules and footnotes are ordinary human work (measured: apple.com/kr); the generated
    # developer-tool look also carries monospace or letter-spaced labels.
    if (ground['L'] <= 20 and ground['C'] <= 12 and ink['L'] >= 80 and restrained and len(habits) >= 2
            and DEVTOOL & set(habits)):
        looks.append({'id': 'dark-mono-accent',
                      'label': 'near-black ground, light ink, one accent, developer-tool habits',
                      'evidence': {'ground': ground['hex'], 'ink': ink['hex'], 'accentHues': hues, 'habits': habits}})
    # A deep navy shares the hue angle but not the look (measured: are.na), so the violet has to be visible.
    violet = [item for item in fp['accents'] if 285 <= item['h'] <= 335 and item['C'] >= 35 and 30 <= item['L'] <= 80
              and (item['pixelShare'] >= 0.005 or item['textShare'] >= 0.01)]
    soft = fp['pills'] >= 1 or fp['roundedShare'] >= 0.4 or fp['shadows'] >= 3
    if violet and fp['gradients'] >= 1 and soft:
        looks.append({'id': 'violet-gradient-saas', 'label': 'violet or indigo accent with gradients, pills or soft cards',
                      'evidence': {'violet': [item['hex'] for item in violet], 'gradients': fp['gradients'],
                                   'pills': fp['pills'], 'roundedShare': fp['roundedShare']}})
    if fp.get('iconTiles', 0) >= 3 and fp.get('cardGrid', 0) >= 3:
        looks.append({'id': 'icon-tile-cards', 'label': 'a small icon in a square beside each heading, on a grid of boxes',
                      'evidence': {'iconTiles': fp['iconTiles'], 'cardGrid': fp['cardGrid']}})
    neon = [item for item in fp['accents'] if item['C'] >= 45 and item['L'] >= 50
            and (130 <= item['h'] <= 250 or 285 <= item['h'] <= 335)]
    if ground['L'] <= 18 and neon and (fp['gradients'] >= 1 or fp['shadows'] >= 3 or fp['monoDecor'] >= 0.02):
        looks.append({'id': 'dark-neon', 'label': 'dark ground with a neon green, cyan or violet accent',
                      'evidence': {'ground': ground['hex'], 'neon': [item['hex'] for item in neon]}})
    return looks


FORM_KEYS = ('scale', 'imageShare', 'hairlinesPer1000', 'trackedSmall', 'numberedHeadings', 'monoDecor',
             'roundedShare', 'shadows', 'gradients', 'pills', 'captions', 'iconTiles', 'cardGrid')
FORM_CAPS = {'scale': 8, 'imageShare': 0.6, 'hairlinesPer1000': 12, 'trackedSmall': 12, 'numberedHeadings': 1,
             'monoDecor': 0.1, 'roundedShare': 1, 'shadows': 12, 'gradients': 4, 'pills': 6, 'captions': 8,
             'iconTiles': 8, 'cardGrid': 12}


def form_distance(one: dict, two: dict) -> float:
    squares = [(min(one.get(key, 0), FORM_CAPS[key]) - min(two.get(key, 0), FORM_CAPS[key])) / FORM_CAPS[key]
               for key in FORM_KEYS]
    return round(math.sqrt(sum(value * value for value in squares) / len(squares)) * 2, 3)


def palette_near(one: dict, two: dict) -> bool:
    if one['darkGround'] != two['darkGround']:
        return False
    if delta_e(one['ground'], two['ground']) >= PALETTE_GROUND or delta_e(one['ink'], two['ink']) >= PALETTE_INK:
        return False
    both_restrained = one['chromaticShare'] <= RESTRAINED and two['chromaticShare'] <= RESTRAINED
    if both_restrained:
        return True
    if one['accents'] and two['accents']:
        return delta_e(one['accents'][0], two['accents'][0]) < PALETTE_ACCENT
    return False


def compare(fp: dict, other: dict) -> dict:
    # Pages without decoration habits all sit at the origin of the form vector, so closeness there says nothing;
    # what repeats across projects is a shared habit.
    shared = sorted(set(tics(fp)) & set(tics(other)))
    return {'ground': round(delta_e(fp['ground'], other['ground']), 1),
            'ink': round(delta_e(fp['ink'], other['ink']), 1),
            'form': form_distance(fp, other),
            'sharedHabits': shared,
            'paletteNear': palette_near(fp, other),
            'formNear': len(shared) >= 2}


def near_recent(fp: dict, ledger: list, recent: int = 5) -> list[dict]:
    rows = []
    for entry in [item for item in ledger if isinstance(item.get('fingerprint'), dict)][-recent:]:
        verdict = compare(fp, entry['fingerprint'])
        if verdict['paletteNear'] or verdict['formNear']:
            rows.append({'project': entry.get('project'), **verdict})
    return rows


def findings(fp: dict, ledger: list | None = None) -> list[dict]:
    out = []
    looks = generated_looks(fp)
    if looks:
        out.append({'id': 'generated-look', 'severity': 'warn', 'width': fp.get('width'),
                    'message': 'The rendered colors and decoration match a look models produce when nothing outside '
                               'the model chose them. Take values from the material or a sourced palette, or record '
                               'why this look belongs to the project.',
                    'count': len(looks),
                    # Same sample shape as the DOM checks; the whole page is the element.
                    'samples': [{'selector': 'html', 'text': look['label'],
                                 'computed': {'look': look['id'], **look['evidence']}} for look in looks]})
    rows = near_recent(fp, ledger or [])
    if rows:
        out.append({'id': 'near-recent', 'severity': 'warn', 'width': fp.get('width'),
                    'message': 'The rendered page shares its palette or its decoration habits with a recent ledger '
                               'entry, whatever the direction labels say.',
                    'count': len(rows),
                    'samples': [{'selector': 'html', 'text': f"close to {row['project']}", 'computed': row}
                                for row in rows[:5]]})
    return out


def read_ledger(path: Path | None) -> list:
    if not path or not path.exists():
        return []
    data = json.loads(path.read_text(encoding='utf-8'))
    return data.get('entries', []) if isinstance(data, dict) else data


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('target')
    parser.add_argument('--width', type=int, default=1440)
    parser.add_argument('--ledger', type=Path)
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--timeout', type=float, default=30)
    args = parser.parse_args(argv)
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='chrome', headless=True)
        try:
            page = browser.new_context(viewport={'width': args.width, 'height': 900}, device_scale_factor=1).new_page()
            page.goto(args.target, wait_until='load', timeout=args.timeout * 1000)
            page.evaluate('document.fonts.ready.then(() => true)')
            try:
                page.wait_for_load_state('networkidle', timeout=5000)
            except Exception:  # long-polling pages never idle; the measurement is still valid
                pass
            fp = measure(page, args.timeout)
        finally:
            browser.close()
    result = {'fingerprint': fp, 'findings': findings(fp, read_ledger(args.ledger))}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ground {fp['ground']['hex']}  ink {fp['ink']['hex']}  accents "
              f"{' '.join(item['hex'] for item in fp['accents'][:3]) or '-'}  chromatic {fp['chromaticShare']}")
        print(f"scale {fp['scale']}  display {fp['display'] or '-'}  habits: {', '.join(tics(fp)) or 'none'}")
        for finding in result['findings']:
            print(f"WARN {finding['id']}: {json.dumps(finding['samples'], ensure_ascii=False)}")
    return 1 if result['findings'] else 0


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())

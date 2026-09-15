#!/usr/bin/env python3
"""Full-page screenshots of a served page at several widths, for looking at the design while building it.

    python shot.py http://127.0.0.1:8000/ [--widths 1440,390] [--out shots] [--slice 1800]

Uses installed Google Chrome through Playwright and waits for load, fonts and the network to settle. Serve the
page (`python -m http.server 8000 --bind 127.0.0.1`); file:// blocks preloaded fonts. `--slice` also writes
top-to-bottom crops of that height, because a 6000px tall PNG is unreadable when it is scaled to fit.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def shoot(target: str, widths: list[int], out: Path, slice_height: int, timeout: int = 30000) -> list[Path]:
    from playwright.sync_api import sync_playwright

    out.mkdir(parents=True, exist_ok=True)
    written = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='chrome', headless=True)
        try:
            for width in widths:
                context = browser.new_context(viewport={'width': width, 'height': 900},
                                              device_scale_factor=1, is_mobile=False)
                page = context.new_page()
                page.goto(target, wait_until='load', timeout=timeout)
                page.evaluate('document.fonts.ready')
                try:
                    page.wait_for_load_state('networkidle', timeout=5000)
                except Exception:  # a page with a long poll never idles; the screenshot is still valid
                    pass
                path = out / f'{width}.png'
                page.screenshot(path=str(path), full_page=True)
                written.append(path)
                if slice_height:
                    written.extend(slice_image(path, slice_height))
                context.close()
        finally:
            browser.close()
    return written


def slice_image(path: Path, height: int) -> list[Path]:
    from PIL import Image

    written = []
    with Image.open(path) as image:
        for index, top in enumerate(range(0, image.height, height), 1):
            part = path.with_name(f'{path.stem}-{index:02d}.png')
            image.crop((0, top, image.width, min(top + height, image.height))).save(part)
            written.append(part)
    return written


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('target')
    parser.add_argument('--widths', default='1440,390')
    parser.add_argument('--out', type=Path, default=Path('shots'))
    parser.add_argument('--slice', type=int, default=1800, help='height of the readable crops; 0 disables them')
    parser.add_argument('--timeout', type=int, default=30000)
    args = parser.parse_args(argv)
    widths = [int(value) for value in args.widths.split(',') if value.strip()]
    if not widths:
        parser.error('--widths needs at least one number')
    if args.target.startswith('file://') or Path(args.target).exists():
        print('shot.py: serve the page over http; file:// blocks preloaded fonts.', file=sys.stderr)
    for path in shoot(args.target, widths, args.out, max(0, args.slice), args.timeout):
        print(path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

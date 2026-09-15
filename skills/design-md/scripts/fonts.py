#!/usr/bin/env python3
"""Fetch licensed fonts once and use the same files for Photoshop comps and the web build.

    python fonts.py list [--role display|text|accent|numerals] [--script ko|latin] [--web-only]
    python fonts.py fetch <id> [<id> ...] --dest assets/fonts [--weights 400,700] [--no-web] [--no-desktop]
    python fonts.py install <id> [<id> ...] --dest assets/fonts     # desktop files into the user font folder
    python fonts.py design-block <id> [<id> ...] --dest assets/fonts [--prefix assets/fonts]
    python fonts.py ps-names <id> [<id> ...] --dest assets/fonts     # PostScript names for photoshop_comp.py

The catalog is references/fonts.json. Only entries with webEmbedding true get web files. Entries with modify false
are served exactly as distributed (no subsetting, no woff2 conversion). Every fetch writes <dest>/<id>/fonts.lock.json
with source URLs, SHA-256 and the license evidence, and regenerates <dest>/fonts.css from all lock files.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import hashlib
import io
import json
import os
import re
import shutil
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CATALOG = HERE.parent / 'references' / 'fonts.json'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
WEIGHT_NAMES = {100: 'Thin', 200: 'ExtraLight', 300: 'Light', 400: 'Regular', 500: 'Medium', 600: 'SemiBold',
                700: 'Bold', 800: 'ExtraBold', 900: 'Black'}
FONT_EXT = ('.otf', '.ttf', '.woff2', '.woff')
FORMATS = {'.woff2': 'woff2', '.woff': 'woff', '.ttf': 'truetype', '.otf': 'opentype'}


def load_catalog(path: Path = CATALOG) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def entry_by_id(catalog: dict, font_id: str) -> dict:
    for entry in catalog['fonts']:
        if entry['id'] == font_id:
            return entry
    raise SystemExit(f'unknown font id "{font_id}". Run: fonts.py list')


def cache_dir() -> Path:
    base = os.environ.get('DESIGN_MD_FONT_CACHE')
    if base:
        return Path(base)
    root = os.environ.get('LOCALAPPDATA') or os.environ.get('XDG_CACHE_HOME') or str(Path.home() / '.cache')
    return Path(root) / 'design-md-fonts'


def http_get_cached(url: str) -> bytes:
    """Large archives are cached by URL; the SHA-256 in fonts.lock.json still records exactly what was used."""
    path = cache_dir() / (hashlib.sha256(url.encode('utf-8')).hexdigest()[:24] + '.bin')
    if path.exists() and path.stat().st_size:
        return path.read_bytes()
    data = http_get(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_bytes(data)
    tmp.replace(path)
    return data


def http_get(url: str, attempts: int = 3) -> bytes:
    last = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.read()
        except Exception as error:  # network errors are retried, then reported with the URL
            last = error
            time.sleep(1 + attempt * 2)
    raise RuntimeError(f'download failed: {url}: {last}')


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def font_info(data: bytes) -> dict:
    """Family, PostScript name, weight, style and variable range read from the font itself."""
    from fontTools.ttLib import TTFont

    font = TTFont(io.BytesIO(data), lazy=True, fontNumber=0)
    names = font['name']
    family = names.getDebugName(16) or names.getDebugName(1) or ''
    subfamily = names.getDebugName(17) or names.getDebugName(2) or ''
    os2 = font['OS/2'] if 'OS/2' in font else None
    weight = int(os2.usWeightClass) if os2 else 400
    italic = bool(os2 and os2.fsSelection & 1) or 'italic' in subfamily.lower()
    info = {'family': family, 'subfamily': subfamily, 'postscript': names.getDebugName(6) or '',
            'weight': weight, 'style': 'italic' if italic else 'normal'}
    if 'fvar' in font:
        for axis in font['fvar'].axes:
            if axis.axisTag == 'wght':
                info['weight'] = f'{int(axis.minValue)} {int(axis.maxValue)}'
                info['variable'] = True
    return info


def weight_ok(weight, wanted: set | None) -> bool:
    if not wanted:
        return True
    if isinstance(weight, str) and ' ' in weight:
        low, high = (int(part) for part in weight.split())
        return any(low <= value <= high for value in wanted)
    return int(weight) in wanted


def to_woff2(data: bytes) -> bytes:
    from fontTools.ttLib import TTFont

    font = TTFont(io.BytesIO(data))
    font.flavor = 'woff2'
    out = io.BytesIO()
    font.save(out)
    return out.getvalue()


def write_file(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def matches(name: str, pattern: str) -> bool:
    return fnmatch.fnmatch(Path(name).name.lower(), pattern.lower())


def zip_members(data: bytes, pattern: str, depth: int = 0) -> list[tuple[str, bytes]]:
    """Font files matching the pattern, looking inside nested zips (some distributions ship zip in zip)."""
    members = []
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for info in archive.infolist():
            name = info.filename
            if info.is_dir() or '__MACOSX' in name or Path(name).name.startswith('._'):
                continue
            if name.lower().endswith('.zip') and depth < 2:
                members.extend(zip_members(archive.read(info), pattern, depth + 1))
            elif matches(name, pattern):
                members.append((Path(name).name, archive.read(info)))
    unique = {}
    for name, payload in members:
        unique.setdefault(name, payload)
    return list(unique.items())


# ---------------------------------------------------------------- sources

def google_metadata(family: str) -> tuple[str, str, list[str]]:
    slug = re.sub(r'[^a-z0-9]', '', family.lower())
    for license_dir in ('ofl', 'apache', 'ufl'):
        base = f'https://raw.githubusercontent.com/google/fonts/main/{license_dir}/{slug}/'
        try:
            metadata = http_get(base + 'METADATA.pb', attempts=1).decode('utf-8')
        except RuntimeError:
            continue
        files = re.findall(r'filename:\s*"([^"]+)"', metadata)
        license_name = (re.search(r'license:\s*"([^"]+)"', metadata) or [None, license_dir.upper()])[1]
        return base, license_name, files
    raise RuntimeError(f'{family}: not found in google/fonts (ofl, apache, ufl)')


def google_css(family: str, weights: list[int]) -> str:
    query = urllib.parse.quote_plus(family)
    urls = []
    if weights:
        urls.append(f'https://fonts.googleapis.com/css2?family={query}:wght@{";".join(str(w) for w in sorted(weights))}&display=swap')
    urls.append(f'https://fonts.googleapis.com/css2?family={query}&display=swap')
    last = None
    for url in urls:
        try:
            return http_get(url, attempts=2).decode('utf-8')
        except RuntimeError as error:
            last = error
    raise RuntimeError(str(last))


def fetch_google(entry, dest, wanted, web, desktop, lock):
    base, license_name, files = google_metadata(entry['family'])
    license_file = {'OFL': 'OFL.txt', 'APACHE2': 'LICENSE.txt', 'UFL': 'UFL.txt'}.get(license_name, 'OFL.txt')
    lock['license'] = {'OFL': 'OFL-1.1', 'APACHE2': 'Apache-2.0', 'UFL': 'UFL-1.0'}.get(license_name, license_name)
    lock['licenseUrl'] = base + license_file
    try:
        data = http_get(base + license_file)
        write_file(dest / license_file, data)
        lock['licenseFile'] = license_file
        # Only a license text read in this run counts as verification.
        lock['verifiedAt'] = dt.date.today().isoformat()
    except RuntimeError as error:
        lock['licenseFile'] = None
        print(f'{entry["id"]}: {license_file} did not download ({error}); the catalog verified date is kept.', file=sys.stderr)
    if desktop:
        for name in files:
            data = http_get(base + urllib.parse.quote(name))
            info = font_info(data)
            if not weight_ok(info['weight'], wanted):
                continue
            write_file(dest / 'desktop' / name, data)
            lock['desktop'].append({'path': f'desktop/{name}', 'url': base + name, 'sha256': sha256(data), **info})
    if web:
        weights = sorted(wanted) if wanted else [w for w in entry.get('weights', []) if isinstance(w, int)]
        css = google_css(entry['family'], weights)
        blocks = re.findall(r'(?:/\*\s*([^*]+?)\s*\*/\s*)?@font-face\s*{([^}]*)}', css)
        rows = []
        for index, (subset, body) in enumerate(blocks):
            url = re.search(r'url\(([^)]+)\)', body).group(1).strip('\'"')
            weight = (re.search(r'font-weight:\s*([^;]+);', body) or [None, '400'])[1].strip()
            style = (re.search(r'font-style:\s*([^;]+);', body) or [None, 'normal'])[1].strip()
            unicode_range = (re.search(r'unicode-range:\s*([^;]+);', body) or [None, None])[1]
            name = f'{entry["id"]}-{weight.replace(" ", "_")}-{style}-{index:03d}.woff2'
            rows.append({'path': f'web/{name}', 'url': url, 'weight': int(weight) if weight.isdigit() else weight,
                         'style': style, 'format': 'woff2', 'unicodeRange': unicode_range, 'subset': (subset or '').strip()})
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=16) as pool:
            payloads = list(pool.map(lambda row: http_get(row['url']), rows))
        for row, data in zip(rows, payloads):
            write_file(dest / row['path'], data)
            lock['web'].append({**row, 'sha256': sha256(data)})


def fetch_npm(entry, dest, wanted, web, desktop, lock):
    source = entry['source']
    root = f'https://cdn.jsdelivr.net/npm/{source["package"]}@{source["version"]}/'
    weights = sorted(wanted) if wanted else entry['weights']
    if source.get('licenseFile'):
        data = http_get(root + source['licenseFile'])
        write_file(dest / Path(source['licenseFile']).name, data)
        lock['licenseFile'] = Path(source['licenseFile']).name
    for weight in weights:
        name = WEIGHT_NAMES[weight]
        for kind, enabled in (('desktop', desktop), ('web', web)):
            if not enabled or not source.get(kind):
                continue
            path = source[kind].replace('{Weight}', name)
            data = http_get(root + path)
            info = font_info(data)
            file_name = Path(path).name
            write_file(dest / kind / file_name, data)
            lock[kind].append({'path': f'{kind}/{file_name}', 'url': root + path, 'sha256': sha256(data),
                               'format': FORMATS[Path(path).suffix.lower()], **info})


def prefer_static(items: list) -> list:
    """Distributions that ship a variable file next to static weights would declare the family twice with overlapping
    weights. Keep the static files when both are present; a variable file alone is kept."""
    if any(info.get('variable') for _, _, info in items) and not all(info.get('variable') for _, _, info in items):
        return [item for item in items if not item[2].get('variable')]
    return items


def fetch_archive_files(entry, dest, wanted, web, desktop, lock, members, url):
    weight_map = entry['source'].get('weightMap', {})
    items = []
    for name, data in members:
        info = font_info(data)
        if Path(name).stem in weight_map:
            info['weight'] = weight_map[Path(name).stem]
        if weight_ok(info['weight'], wanted):
            items.append((name, data, info))
    for name, data, info in prefer_static(items):
        if desktop:
            write_file(dest / 'desktop' / name, data)
            lock['desktop'].append({'path': f'desktop/{name}', 'url': url, 'sha256': sha256(data),
                                    'format': FORMATS[Path(name).suffix.lower()], **info})
        if web and not entry['source'].get('web'):
            if entry.get('modify', False):
                web_name = Path(name).stem + '.woff2'
                web_data = to_woff2(data)
                lock['web'].append({'path': f'web/{web_name}', 'derivedFrom': f'desktop/{name}', 'sha256': sha256(web_data),
                                    'format': 'woff2', **info})
            else:
                web_name, web_data = name, data
                lock['web'].append({'path': f'web/{web_name}', 'url': url, 'sha256': sha256(web_data), 'unchanged': True,
                                    'format': FORMATS[Path(name).suffix.lower()], **info})
            write_file(dest / 'web' / web_name, web_data)


def fetch_zip(entry, dest, wanted, web, desktop, lock):
    source = entry['source']
    data = http_get_cached(source['url'])
    lock['archiveSha256'] = sha256(data)
    members = zip_members(data, source.get('desktop', '*.otf'))
    if not members:
        raise RuntimeError(f'{entry["id"]}: no files match {source.get("desktop")} in {source["url"]}')
    fetch_archive_files(entry, dest, wanted, web, desktop, lock, members, source['url'])
    if web and isinstance(source.get('web'), dict):
        web_data = http_get_cached(source['web']['url'])
        for name, font in zip_members(web_data, source['web']['glob']):
            info = font_info(font)
            if not weight_ok(info['weight'], wanted):
                continue
            write_file(dest / 'web' / name, font)
            lock['web'].append({'path': f'web/{name}', 'url': source['web']['url'], 'sha256': sha256(font),
                                'format': FORMATS[Path(name).suffix.lower()], **info})
    if source.get('licenseUrlRaw'):
        write_file(dest / 'LICENSE.txt', http_get(source['licenseUrlRaw']))
        lock['licenseFile'] = 'LICENSE.txt'
    else:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for name in archive.namelist():
                if re.search(r'(licen[cs]e|ofl|저작권)[^/]*\.(txt|md|pdf|html)$', name, re.I) and '__MACOSX' not in name:
                    write_file(dest / Path(name).name, archive.read(name))
                    lock['licenseFile'] = Path(name).name
                    break


def fetch_raw(entry, dest, wanted, web, desktop, lock):
    source = entry['source']
    members = [(name, http_get(source['base'] + name)) for name in source['files']]
    fetch_archive_files(entry, dest, wanted, web, desktop, lock, members, source['base'])
    if source.get('licenseFile'):
        write_file(dest / source['licenseFile'], http_get(source['base'] + source['licenseFile']))
        lock['licenseFile'] = source['licenseFile']


FETCHERS = {'google': fetch_google, 'npm': fetch_npm, 'zip': fetch_zip, 'raw': fetch_raw}


def fetch(entry: dict, root: Path, wanted: set | None, web: bool, desktop: bool) -> dict:
    kind = entry['source']['kind']
    if kind == 'manual':
        raise SystemExit(f'{entry["id"]}: manual source. {entry["source"].get("steps", "")} Page: {entry["source"]["page"]}')
    if web and not entry.get('webEmbedding'):
        print(f'{entry["id"]}: webEmbedding is false, fetching desktop files only (Photoshop, images, print).', file=sys.stderr)
        web = False
    final = root / entry['id']
    # Download into a sibling folder and swap at the end: a failed refetch must not delete a working installation.
    dest = root / f'.{entry["id"]}.partial'
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    lock = {'id': entry['id'], 'family': entry['family'], 'license': entry['license'], 'licenseUrl': entry.get('licenseUrl'),
            'webEmbedding': entry['webEmbedding'], 'modify': entry.get('modify', False), 'verified': entry['verified'],
            'evidence': entry.get('evidence'), 'source': entry['source'], 'fetchedAt': dt.datetime.now().astimezone().isoformat(timespec='seconds'),
            'desktop': [], 'web': [], 'licenseFile': None}
    try:
        FETCHERS[kind](entry, dest, wanted, web, desktop, lock)
        if desktop and not lock['desktop']:
            raise RuntimeError(f'{entry["id"]}: no desktop files matched weights {sorted(wanted or [])}')
        if web and not lock['web']:
            raise RuntimeError(f'{entry["id"]}: no web files produced')
        if not lock['licenseFile']:
            # Some distributions ship no license text. Keep the verified wording and a copy of the license page.
            text = (f'{entry["family"]}\nLicense: {lock["license"]}\nLicense page: {entry.get("licenseUrl")}\n'
                    f'Verified: {entry["verified"]}\n\n{entry.get("evidence") or ""}\n')
            (dest / 'LICENSE-EVIDENCE.txt').write_text(text, encoding='utf-8')
            lock['licenseFile'] = 'LICENSE-EVIDENCE.txt'
            if entry.get('licenseUrl'):
                try:
                    write_file(dest / 'LICENSE-PAGE.html', http_get(entry['licenseUrl'], attempts=2))
                    lock['licensePage'] = 'LICENSE-PAGE.html'
                except RuntimeError as error:
                    print(f'{entry["id"]}: could not save the license page ({error}). Save {entry["licenseUrl"]} by hand '
                          'before redistributing these files.', file=sys.stderr)
        (dest / 'fonts.lock.json').write_text(json.dumps(lock, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    except BaseException:
        shutil.rmtree(dest, ignore_errors=True)
        raise
    if final.exists():
        shutil.rmtree(final)
    dest.replace(final)
    return lock


# ---------------------------------------------------------------- outputs

def read_locks(root: Path) -> list[dict]:
    return [json.loads(path.read_text(encoding='utf-8')) for path in sorted(root.glob('*/fonts.lock.json'))]


def css_for(locks: list[dict]) -> str:
    out = ['/* Generated by design-md fonts.py from fonts.lock.json files. Do not edit by hand. */']
    for lock in locks:
        if not lock['web'] or not lock.get('webEmbedding'):
            continue  # a face whose license forbids web embedding never reaches CSS, even with stale web entries
        out.append(f'/* {lock["family"]}: {lock["license"]}, verified {lock["verified"]}, {lock.get("licenseUrl") or ""} */')
        for item in lock['web']:
            lines = [f'  font-family: "{lock["family"]}";',
                     f'  src: url("./{lock["id"]}/{item["path"]}") format("{item["format"]}");',
                     f'  font-weight: {item["weight"]};',
                     f'  font-style: {item.get("style", "normal")};',
                     '  font-display: swap;']
            if item.get('unicodeRange'):
                lines.append(f'  unicode-range: {item["unicodeRange"]};')
            out.append('@font-face {\n' + '\n'.join(lines) + '\n}')
    return '\n'.join(out) + '\n'


def source_page(entry: dict) -> str:
    """The official distribution a person can open to re-check the license, not the license file itself."""
    source = entry['source']
    if source.get('page'):
        return source['page']
    if source['kind'] == 'google':
        return f'https://fonts.google.com/specimen/{entry["family"].replace(" ", "+")}'
    if source['kind'] == 'npm':
        return f'https://www.npmjs.com/package/{source["package"]}/v/{source["version"]}'
    github = re.match(r'https://(?:raw\.githubusercontent\.com|github\.com)/([^/]+)/([^/]+)/', source.get('base') or source.get('url') or '')
    if github:
        return f'https://github.com/{github.group(1)}/{github.group(2)}'
    # Direct archive links (131 MB zips, CDN hashes) are not a page a person can re-check; the license page is.
    return entry.get('licenseUrl') or source.get('url') or ''


def design_block(locks: list[dict], catalog: dict, prefix: str) -> str:
    prefix = prefix.rstrip('/')
    lines = ['fonts:']
    for lock in locks:
        entry = entry_by_id(catalog, lock['id'])
        token = lock['id'].replace('-', '_')
        source = source_page(entry)
        lines += [f'  {token}:',
                  f'    family: "{lock["family"]}"',
                  f'    source: "{source}"',
                  f'    license: "{lock["license"]}"',
                  f'    licenseUrl: "{lock.get("licenseUrl") or ""}"',
                  f'    webEmbedding: {"true" if lock["webEmbedding"] else "false"}',
                  f'    verified: "{lock.get("verifiedAt") or lock["verified"]}"']
        web_files = lock['web'] if lock.get('webEmbedding') else []
        if web_files and not any(item.get('unicodeRange') for item in web_files):
            lines.append('    files:')
            for item in web_files:
                lines += [f'      - path: "{prefix}/{lock["id"]}/{item["path"]}"',
                          f'        weight: "{item["weight"]}"' if isinstance(item['weight'], str) else f'        weight: {item["weight"]}',
                          f'        style: {item.get("style", "normal")}',
                          f'        format: {item["format"]}']
        elif web_files:
            lines.append(f'    stylesheet: "{prefix}/fonts.css"')
    return '\n'.join(lines) + '\n'


def install(locks: list[dict], root: Path) -> list[str]:
    installed = []
    if sys.platform == 'win32':
        import ctypes
        import winreg

        target = Path(os.environ['LOCALAPPDATA']) / 'Microsoft' / 'Windows' / 'Fonts'
        target.mkdir(parents=True, exist_ok=True)
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows NT\CurrentVersion\Fonts')
        for lock in locks:
            for item in lock['desktop']:
                source = root / lock['id'] / item['path']
                destination = target / source.name
                shutil.copy2(source, destination)
                label = f'{item["family"]} {item["subfamily"]}'.strip()
                kind = 'OpenType' if source.suffix.lower() == '.otf' else 'TrueType'
                winreg.SetValueEx(key, f'{label} ({kind})', 0, winreg.REG_SZ, str(destination))
                installed.append(str(destination))
        winreg.CloseKey(key)
        ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x001D, 0, 0, 0x0002, 1000, None)  # WM_FONTCHANGE
    else:
        target = Path.home() / ('Library/Fonts' if sys.platform == 'darwin' else '.local/share/fonts')
        target.mkdir(parents=True, exist_ok=True)
        for lock in locks:
            for item in lock['desktop']:
                source = root / lock['id'] / item['path']
                shutil.copy2(source, target / source.name)
                installed.append(str(target / source.name))
        if sys.platform.startswith('linux') and shutil.which('fc-cache'):
            os.system('fc-cache -f >/dev/null 2>&1')
    return installed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    p_list = sub.add_parser('list')
    p_list.add_argument('--role')
    p_list.add_argument('--script')
    p_list.add_argument('--web-only', action='store_true')
    for name in ('fetch', 'install', 'design-block', 'ps-names'):
        p = sub.add_parser(name)
        p.add_argument('ids', nargs='+')
        p.add_argument('--dest', type=Path, required=True)
        if name == 'fetch':
            p.add_argument('--weights', help='comma separated, e.g. 400,700')
            p.add_argument('--no-web', action='store_true')
            p.add_argument('--no-desktop', action='store_true')
        if name == 'design-block':
            p.add_argument('--prefix', help='path prefix written into DESIGN.md (default: --dest as given)')
    args = parser.parse_args(argv)
    catalog = load_catalog()

    if args.command == 'list':
        for entry in catalog['fonts']:
            if args.role and args.role not in entry['roles']:
                continue
            if args.script and args.script not in entry['script']:
                continue
            if args.web_only and not entry['webEmbedding']:
                continue
            web = 'web' if entry['webEmbedding'] else 'NO-WEB'
            modify = '' if entry.get('modify', False) else ' unmodified-only'
            print(f'{entry["id"]:<22} {entry["family"]:<22} {entry["category"]:<11} {",".join(entry["roles"]):<16} '
                  f'{web}{modify:<16} {entry["license"]}')
        print('\npairings: ' + ', '.join(f'{p["id"]} ({p["label"]})' for p in catalog['pairings']))
        return 0

    if args.command == 'fetch':
        wanted = {int(value) for value in args.weights.split(',')} if args.weights else None
        for font_id in args.ids:
            lock = fetch(entry_by_id(catalog, font_id), args.dest, wanted, not args.no_web, not args.no_desktop)
            print(f'{font_id}: desktop {len(lock["desktop"])} files, web {len(lock["web"])} files, license {lock["license"]}')
        (args.dest / 'fonts.css').write_text(css_for(read_locks(args.dest)), encoding='utf-8')
        print(f'wrote {args.dest / "fonts.css"}')
        return 0

    locks = []
    for font_id in args.ids:
        path = args.dest / font_id / 'fonts.lock.json'
        if not path.exists():
            print(f'{font_id}: not fetched into {args.dest}. Run fetch first.', file=sys.stderr)
            return 2
        locks.append(json.loads(path.read_text(encoding='utf-8')))
    if args.command == 'install':
        for path in install(locks, args.dest):
            print(f'installed {path}')
        print('Restart Photoshop if it was running so it lists the new fonts.')
    elif args.command == 'design-block':
        print(design_block(locks, catalog, args.prefix or args.dest.as_posix()), end='')
    else:
        for lock in locks:
            for item in lock['desktop']:
                note = ('\tvariable file: Photoshop opens the default instance, so set the weight axis by hand or use a '
                        'static file') if item.get('variable') else ''
                print(f'{lock["id"]}\t{item["weight"]}\t{item["style"]}\t{item["postscript"]}{note}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

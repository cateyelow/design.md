#!/usr/bin/env python3
"""Build a layered Photoshop comp (PSD + PNG) from a JSON spec, typeset with the real font files.

    python photoshop_comp.py comp.json [--restart] # Windows with Photoshop installed (COM automation)
    python photoshop_comp.py comp.json --dry-run  # validate the spec and print the generated script
    python photoshop_comp.py --list-fonts [--match Pretendard]

Spec (pixels, top-left origin):
{
  "canvas": {"width": 1440, "height": 2000, "background": "#f4f2ec"},
  "output": {"psd": "comps/desktop.psd", "png": "comps/desktop.png"},
  "layers": [
    {"type": "rect",  "name": "band", "x": 0, "y": 0, "width": 1440, "height": 880, "color": "#1f1d1a"},
    {"type": "image", "name": "hero", "path": "images/hero.png", "x": 760, "y": 0, "width": 680, "height": 880,
     "focus": [0.5, 0.4], "grain": 2.0},
    {"type": "text",  "name": "headline", "text": "식빵은 7시 30분에 나옵니다", "font": "MaruBuriot-Bold",
     "size": 72, "leading": 90, "tracking": -20, "color": "#f4f2ec", "x": 96, "y": 200, "width": 600, "height": 320,
     "align": "left"}
  ]
}

Fonts are PostScript names (fonts.py ps-names). Missing fonts stop the build before any document is created.
Layers are stacked in list order (first = bottom). Image layers are cropped to cover their box around `focus`.
Paths in the spec are resolved relative to the spec file. The comp is a reference for implementation and for a
person to refine in Photoshop; the HTML stays the final source of truth.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HEX = re.compile(r'^#?[0-9a-fA-F]{6}$')
ALIGN = {'left': 'Justification.LEFT', 'center': 'Justification.CENTER', 'right': 'Justification.RIGHT'}


class SpecError(ValueError):
    pass


def _number(layer: dict, key: str, index: int, minimum: float | None = None) -> float:
    value = layer.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise SpecError(f'layers[{index}].{key} must be a number')
    if minimum is not None and value < minimum:
        raise SpecError(f'layers[{index}].{key} must be >= {minimum}')
    return float(value)


def load_spec(path: Path) -> dict:
    spec = json.loads(path.read_text(encoding='utf-8'))
    base = path.parent
    canvas = spec.get('canvas') or {}
    for key in ('width', 'height'):
        if not isinstance(canvas.get(key), int) or canvas[key] <= 0:
            raise SpecError(f'canvas.{key} must be a positive integer')
    if canvas.get('background') and not HEX.match(canvas['background']):
        raise SpecError('canvas.background must be #RRGGBB')
    output = spec.get('output') or {}
    if not output.get('psd') and not output.get('png'):
        raise SpecError('output needs psd and/or png')
    for key in ('psd', 'png'):
        if output.get(key):
            output[key] = str((base / output[key]).resolve())
    layers = spec.get('layers')
    if not isinstance(layers, list) or not layers:
        raise SpecError('layers must be a non-empty list')
    for index, layer in enumerate(layers):
        kind = layer.get('type')
        if kind not in ('rect', 'image', 'text'):
            raise SpecError(f'layers[{index}].type must be rect, image or text')
        for key in ('x', 'y'):
            _number(layer, key, index)
        for key in ('width', 'height'):
            _number(layer, key, index, minimum=1)
        if kind in ('rect', 'text') and not HEX.match(str(layer.get('color', ''))):
            raise SpecError(f'layers[{index}].color must be #RRGGBB')
        if kind == 'image':
            source = (base / str(layer.get('path', ''))).resolve()
            if not source.is_file():
                raise SpecError(f'layers[{index}].path not found: {source}')
            layer['path'] = str(source)
            focus = layer.get('focus', [0.5, 0.5])
            if (not isinstance(focus, list) or len(focus) != 2
                    or not all(isinstance(v, (int, float)) and 0 <= v <= 1 for v in focus)):
                raise SpecError(f'layers[{index}].focus must be [x, y] between 0 and 1')
            layer['focus'] = focus
            if 'grain' in layer:
                _number(layer, 'grain', index, minimum=0)
        if kind == 'text':
            if not isinstance(layer.get('text'), str) or not layer['text']:
                raise SpecError(f'layers[{index}].text must be a non-empty string')
            if not isinstance(layer.get('font'), str) or not layer['font']:
                raise SpecError(f'layers[{index}].font must be a PostScript name')
            _number(layer, 'size', index, minimum=1)
            if 'leading' in layer:
                _number(layer, 'leading', index, minimum=1)
            if 'tracking' in layer:
                _number(layer, 'tracking', index)
            if layer.get('align', 'left') not in ALIGN:
                raise SpecError(f'layers[{index}].align must be left, center or right')
    return spec


def fonts_needed(spec: dict) -> list[str]:
    return sorted({layer['font'] for layer in spec['layers'] if layer['type'] == 'text'})


JSX_TEMPLATE = r'''
(function () {
  var SPEC = __SPEC__;
  function hex(value) { var c = new SolidColor(); c.rgb.hexValue = value.replace('#', ''); return c; }
  function px(v) { return new UnitValue(v, 'px'); }
  function num(v) { return parseFloat(String(v)); }
  var keepRuler = app.preferences.rulerUnits, keepType = app.preferences.typeUnits;
  app.preferences.rulerUnits = Units.PIXELS;
  app.preferences.typeUnits = TypeUnits.PIXELS;
  var doc = null;
  try {
    var available = {};
    for (var f = 0; f < app.fonts.length; f++) { available[app.fonts[f].postScriptName] = true; }
    var missing = [];
    for (var i = 0; i < SPEC.layers.length; i++) {
      var needed = SPEC.layers[i];
      if (needed.type === 'text' && !available[needed.font]) { missing.push(needed.font); }
    }
    if (missing.length) { return 'MISSING_FONTS|' + missing.join(','); }
    doc = app.documents.add(SPEC.canvas.width, SPEC.canvas.height, 72, SPEC.name || 'comp',
                            NewDocumentMode.RGB, DocumentFill.WHITE);
    if (SPEC.canvas.background) {
      doc.selection.selectAll();
      doc.selection.fill(hex(SPEC.canvas.background));
      doc.selection.deselect();
    }
    for (var n = 0; n < SPEC.layers.length; n++) {
      var L = SPEC.layers[n];
      if (L.type === 'rect') {
        var rect = doc.artLayers.add();
        rect.name = L.name || ('rect ' + n);
        doc.selection.select([[L.x, L.y], [L.x + L.width, L.y], [L.x + L.width, L.y + L.height], [L.x, L.y + L.height]]);
        doc.selection.fill(hex(L.color));
        doc.selection.deselect();
      } else if (L.type === 'image') {
        var src = app.open(new File(L.path));
        if (src.mode !== DocumentMode.RGB) { src.changeMode(ChangeMode.RGB); }
        // mergeVisibleLayers keeps transparency; flatten would fill a cut-out PNG with white.
        if (src.layers.length > 1) { src.mergeVisibleLayers(); }
        var iw = num(src.width), ih = num(src.height);
        var scale = Math.max(L.width / iw, L.height / ih);
        var cw = L.width / scale, ch = L.height / scale;
        var left = Math.min(Math.max(iw * L.focus[0] - cw / 2, 0), iw - cw);
        var top = Math.min(Math.max(ih * L.focus[1] - ch / 2, 0), ih - ch);
        src.crop([px(left), px(top), px(left + cw), px(top + ch)]);
        src.resizeImage(px(L.width), px(L.height), 72, ResampleMethod.BICUBIC);
        src.selection.selectAll();
        src.selection.copy();
        src.close(SaveOptions.DONOTSAVECHANGES);
        app.activeDocument = doc;
        var pasted = doc.paste();
        pasted.name = L.name || ('image ' + n);
        var b = pasted.bounds;
        pasted.translate(px(L.x - num(b[0])), px(L.y - num(b[1])));
        if (L.grain) { pasted.applyAddNoise(L.grain, NoiseDistribution.GAUSSIAN, true); }
      } else if (L.type === 'text') {
        var layer = doc.artLayers.add();
        layer.kind = LayerKind.TEXT;
        layer.name = L.name || ('text ' + n);
        var t = layer.textItem;
        t.kind = TextType.PARAGRAPHTEXT;
        t.contents = L.text.split('\n').join('\r');
        t.font = L.font;
        t.size = px(L.size);
        t.color = hex(L.color);
        t.justification = eval(L.alignJs);
        if (L.leading) { t.useAutoLeading = false; t.leading = px(L.leading); }
        if (L.tracking) { t.tracking = L.tracking; }
        t.position = [px(L.x), px(L.y)];
        t.width = px(L.width);
        t.height = px(L.height);
        if (t.font !== L.font) { throw new Error('Photoshop substituted ' + t.font + ' for ' + L.font); }
      }
    }
    if (SPEC.output.png) {
      var opts = new ExportOptionsSaveForWeb();
      opts.format = SaveDocumentType.PNG;
      opts.PNG8 = false;
      doc.exportDocument(new File(SPEC.output.png), ExportType.SAVEFORWEB, opts);
    }
    if (SPEC.output.psd) {
      var psd = new PhotoshopSaveOptions();
      psd.layers = true;
      doc.saveAs(new File(SPEC.output.psd), psd, true);
    }
    return 'OK|' + doc.layers.length;
  } catch (e) {
    return 'ERROR|' + e.message + ' (line ' + e.line + ')';
  } finally {
    if (doc) { doc.close(SaveOptions.DONOTSAVECHANGES); }
    app.preferences.rulerUnits = keepRuler;
    app.preferences.typeUnits = keepType;
  }
})();
'''


def build_jsx(spec: dict) -> str:
    payload = json.loads(json.dumps(spec))
    for layer in payload['layers']:
        if layer['type'] == 'text':
            layer['alignJs'] = ALIGN[layer.get('align', 'left')]
        for key in ('path',):
            if key in layer:
                layer[key] = layer[key].replace('\\', '/')
    for key in ('psd', 'png'):
        if payload['output'].get(key):
            payload['output'][key] = payload['output'][key].replace('\\', '/')
    # ExtendScript is ES3: no JSON object, but a JSON literal is a valid object literal. ensure_ascii keeps it ASCII.
    return JSX_TEMPLATE.replace('__SPEC__', json.dumps(payload, ensure_ascii=True))


def photoshop():
    if sys.platform != 'win32':
        raise SystemExit('Photoshop automation here uses Windows COM. On other systems run with --dry-run and build the comp by hand.')
    try:
        import pythoncom
        import win32com.client
    except ImportError:
        raise SystemExit('pywin32 is required: python -m pip install pywin32')
    pythoncom.CoInitialize()
    try:
        app = win32com.client.Dispatch('Photoshop.Application')
    except Exception as error:
        raise SystemExit(f'Photoshop COM is not available ({error}). Is Photoshop installed?')
    app.DisplayDialogs = 3
    return app


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('spec', nargs='?', type=Path)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--list-fonts', action='store_true')
    parser.add_argument('--match', default='')
    parser.add_argument('--restart', action='store_true',
                        help='if fonts are missing and Photoshop has no open documents, restart it once and retry')
    args = parser.parse_args(argv)

    if args.list_fonts:
        app = photoshop()
        pattern = args.match.replace('\\', '\\\\').replace("'", "\\'")
        script = ("(function(){var o=[];for(var i=0;i<app.fonts.length;i++){var f=app.fonts[i];"
                  f"if(!'{pattern}'||(f.name+' '+f.postScriptName).toLowerCase().indexOf('{pattern}'.toLowerCase())>=0)"
                  "o.push(f.postScriptName+'\\t'+f.name);}return o.join('\\n');})();")
        print(app.DoJavaScript(script))
        return 0
    if not args.spec:
        parser.error('spec is required')
    try:
        spec = load_spec(args.spec)
    except (SpecError, json.JSONDecodeError) as error:
        print(f'invalid spec: {error}', file=sys.stderr)
        return 2
    jsx = build_jsx(spec)
    if args.dry_run:
        print(json.dumps({'fonts': fonts_needed(spec), 'layers': len(spec['layers']), 'output': spec['output']},
                         ensure_ascii=False, indent=2))
        print(jsx)
        return 0
    for key in ('psd', 'png'):
        if spec['output'].get(key):
            Path(spec['output'][key]).parent.mkdir(parents=True, exist_ok=True)
    app = photoshop()
    result = str(app.DoJavaScript(jsx))
    status, _, detail = result.partition('|')
    if status == 'MISSING_FONTS' and args.restart:
        # Photoshop reads the font list at launch. Restart only when nothing is open, so no one loses work.
        if int(app.Documents.Count) > 0:
            print('Photoshop has open documents; not restarting it. Save and close them, or restart it yourself.',
                  file=sys.stderr)
        else:
            import time

            app.Quit()
            del app
            time.sleep(8)
            app = photoshop()
            result = str(app.DoJavaScript(jsx))
            status, _, detail = result.partition('|')
    if status == 'OK':
        print(json.dumps({'status': 'ok', 'layers': int(detail), 'output': spec['output']}, ensure_ascii=False, indent=2))
        return 0
    if status == 'MISSING_FONTS':
        print(f'Photoshop does not list these fonts: {detail}\nInstall them with fonts.py install, restart Photoshop, '
              'and check names with --list-fonts.', file=sys.stderr)
        return 3
    print(f'Photoshop script failed: {result}', file=sys.stderr)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())

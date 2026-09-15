#!/usr/bin/env python3
"""Collect review evidence from a landing page using installed Google Chrome.

Requires Python 3.11 and Playwright (no downloaded Playwright browser needed).
The DOM checks inspect the top document, including content below the fold, after
load/fonts/idle. They do not inspect iframe or shadow-root internals, pseudo-
elements, canvas text, or interactive states. Geometry, copy, and color checks
are heuristics, not a design verdict or a complete accessibility audit. Contrast
uses ancestor backgrounds; it cannot account for overlapping sibling layers.
Font fallback samples three nodes and compares their dominant CDP font, so
mixed-script or mixed-font nodes can hide a minority fallback.

Counts are finding records per severity, not the number of matching elements.
Each finding's count is its number of matches (phrase occurrences for clichés).

At the widest width the page is also fingerprinted (fingerprint.py): measured ground,
ink and accent colors and decoration habits. `generated-look` flags a palette and
habits models fall back to; `near-recent` (with --ledger) flags a page that repeats a
recent ledger entry's palette or habits, whatever its direction labels say.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit
from urllib.request import url2pathname

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fingerprint  # noqa: E402


DOM_AUDIT = r"""() => {
    const findings = [], skipped = [];
    const styles = new Map(), rectangles = new Map(), visibility = new Map();
    const style = el => {
        if (!styles.has(el)) styles.set(el, getComputedStyle(el));
        return styles.get(el);
    };
    const rect = el => {
        if (!rectangles.has(el)) rectangles.set(el, el.getBoundingClientRect());
        return rectangles.get(el);
    };
    const norm = s => (s || '').replace(/\s+/g, ' ').trim();
    const number = s => parseFloat(s) || 0;
    const firstFamily = el => {
        // A quoted family may itself contain a comma.
        const match = style(el).fontFamily.match(/^\s*(?:"([^"]+)"|'([^']+)'|([^,]+))/);
        return match ? (match[1] || match[2] || match[3]).trim() : '';
    };
    function visible(el) {
        if (visibility.has(el)) return visibility.get(el);
        let result = !el.closest('script, style, template, noscript, head');
        const box = rect(el), css = style(el);
        result = result && (css.display === 'contents' || (box.width > 0 && box.height > 0)) &&
            css.visibility !== 'hidden' && css.visibility !== 'collapse';
        for (let p = el; result && p; p = p.parentElement) {
            const s = style(p);
            if (s.display === 'none' || number(s.opacity) === 0 ||
                s.contentVisibility === 'hidden') result = false;
            // The root scroller is intentionally not clipped to the viewport:
            // full-page content below the fold is part of this audit.
            if (p !== el && p !== document.body && p !== document.documentElement &&
                css.display !== 'contents') {
                const clip = rect(p);
                if (/(hidden|clip|scroll|auto)/.test(s.overflowX) &&
                    (box.right <= clip.left || box.left >= clip.right)) result = false;
                if (/(hidden|clip|scroll|auto)/.test(s.overflowY) &&
                    (box.bottom <= clip.top || box.top >= clip.bottom)) result = false;
            }
        }
        visibility.set(el, result);
        return result;
    }
    function selector(el) {
        const parts = [];
        for (let p = el; p; p = p.parentElement) {
            const tag = p.localName;
            const siblings = p.parentElement ?
                [...p.parentElement.children].filter(n => n.localName === tag) : [p];
            parts.unshift(CSS.escape(tag) + (siblings.length > 1 ?
                `:nth-of-type(${siblings.indexOf(p) + 1})` : ''));
        }
        return parts.join(' > ');
    }
    const all = [...document.querySelectorAll('*')];
    const elements = all.filter(visible);
    // Text nodes are assigned both to their styled owner (contrast/fonts) and
    // nearest block (copy). Inline spans do not double-count entire paragraphs.
    const direct = new Map(), blocks = new Map();
    const walker = document.createTreeWalker(document.body || document.documentElement,
        NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
        const node = walker.currentNode, el = node.parentElement;
        if (!el || !visible(el) || !norm(node.textContent) || el.closest('svg')) continue;
        const range = document.createRange();
        range.selectNodeContents(node);
        if (![...range.getClientRects()].some(r => r.width > 0 && r.height > 0)) continue;
        direct.set(el, (direct.get(el) || '') + node.textContent);
        let block = el;
        while (block.parentElement && /^(inline|contents)$/.test(style(block).display)) {
            block = block.parentElement;
        }
        blocks.set(block, (blocks.get(block) || '') + node.textContent);
    }
    const textRows = [...direct].map(([el, text]) => ({el, text: norm(text)}));
    const copyRows = [...blocks].map(([el, text]) => ({el, text: norm(text)}));
    function visibleText(el) {
        return norm(textRows.filter(row => el === row.el || el.contains(row.el))
            .map(row => row.text).join(' '));
    }
    function sample(el, computed = {}, text = null) {
        return {selector: selector(el), text: (text ?? visibleText(el)).slice(0, 200), computed};
    }
    function add(id, severity, message, samples, count = samples.length) {
        if (count) findings.push({id, severity, message, count, samples: samples.slice(0, 5)});
    }
    function skip(id, reason) { skipped.push({id, reason}); }
    function check(id, fn) {
        try { fn(); } catch (error) { skip(id, `DOM check failed: ${error.message}`); }
    }
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 1;
    const ctx = canvas.getContext('2d', {willReadFrequently: true});
    const colors = new Map();
    function color(value) {
        if (colors.has(value)) return colors.get(value);
        if (!CSS.supports('color', value)) return null;
        ctx.clearRect(0, 0, 1, 1);
        ctx.fillStyle = value;
        ctx.fillRect(0, 0, 1, 1);
        const bytes = [...ctx.getImageData(0, 0, 1, 1).data];
        const result = [bytes[0], bytes[1], bytes[2], bytes[3] / 255];
        colors.set(value, result);
        return result;
    }
    function colorTokens(value) {
        return (value.match(/(?:rgba?|hsla?|hwb|oklab|oklch|lab|lch|color)\([^)]*\)|#[a-f\d]{3,8}\b|\b[a-z]+\b/gi) || [])
            .map(token => ({token, rgba: color(token)})).filter(item => item.rgba);
    }
    function hsl(rgba) {
        const [r, g, b] = rgba.map(v => v / 255);
        const max = Math.max(r, g, b), min = Math.min(r, g, b), d = max - min;
        const light = (max + min) / 2;
        let hue = 0;
        if (d) {
            if (max === r) hue = ((g - b) / d) % 6;
            else if (max === g) hue = (b - r) / d + 2;
            else hue = (r - g) / d + 4;
        }
        return [(hue * 60 + 360) % 360, d ? d / (1 - Math.abs(2 * light - 1)) : 0, light];
    }
    function luminance(rgb) {
        const linear = rgb.slice(0, 3).map(v => {
            v /= 255;
            return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
        });
        return linear[0] * 0.2126 + linear[1] * 0.7152 + linear[2] * 0.0722;
    }
    function over(front, back) {
        const a = front[3] + back[3] * (1 - front[3]);
        return [0, 1, 2].map(i => a ?
            (front[i] * front[3] + back[i] * back[3] * (1 - front[3])) / a : 0).concat(a);
    }
    function background(el, inspectImages = true) {
        let rgba = [0, 0, 0, 0];
        for (let p = el; p; p = p.parentElement) {
            const css = style(p);
            if (inspectImages && css.backgroundImage !== 'none') {
                return {reason: `background-image at ${selector(p)}`};
            }
            const c = color(css.backgroundColor);
            if (!c) return {reason: `unresolved background-color at ${selector(p)}`};
            rgba = over(rgba, c);
            if (rgba[3] >= 0.999) return {rgba};
        }
        return {rgba: over(rgba, [255, 255, 255, 1])};
    }
    function radii(el) {
        const css = style(el), box = rect(el);
        return ['TopLeft', 'TopRight', 'BottomRight', 'BottomLeft'].map(corner => {
            const parts = css[`border${corner}Radius`].split(/\s+/);
            const length = (v, size) => v.endsWith('%') ? number(v) * size / 100 : number(v);
            return Math.min(length(parts[0], box.width), length(parts[1] || parts[0], box.height));
        });
    }
    const sides = ['Top', 'Right', 'Bottom', 'Left'];
    const borders = el => sides.map(side => number(style(el)[`border${side}Width`]));
    const hasBackground = el => (color(style(el).backgroundColor)?.[3] || 0) > 0 ||
        style(el).backgroundImage !== 'none';
    const hasBorder = el => borders(el).some((width, i) => width > 0 &&
        (color(style(el)[`border${sides[i]}Color`])?.[3] || 0) > 0);
    const cardLike = el => Math.max(...radii(el)) > 0 &&
        sides.some(side => number(style(el)[`padding${side}`]) > 0) &&
        (hasBackground(el) || hasBorder(el));
    const cards = elements.filter(cardLike);
    const headings = elements.filter(el => el.matches('h1, h2'));
    const h1 = headings.find(el => el.matches('h1'));
    const hero = h1?.closest('section, header, main, article') || h1?.parentElement;
    const genericDesignFonts = new Set(['inter', 'geist', 'geist sans', 'space grotesk',
        'instrument serif', 'poppins', 'montserrat', 'roboto', 'open sans', 'dm sans',
        'plus jakarta sans', 'manrope']);

    check('font-generic', () => {
        const candidates = new Set([...headings, ...textRows.filter(row =>
            !row.el.closest('h1, h2, h3, h4, h5, h6')).map(row => row.el)]);
        const matches = [...candidates].filter(el => genericDesignFonts.has(firstFamily(el).toLowerCase()));
        add('font-generic', 'warn', 'Common landing-page font declared first.', matches.map(el =>
            sample(el, {fontFamily: style(el).fontFamily, firstFamily: firstFamily(el)})));
    });
    check('single-family', () => {
        const nodes = elements.filter(el => el.matches('h1, h2, p') && visibleText(el));
        if (['h1', 'h2', 'p'].every(tag => nodes.some(el => el.matches(tag))) &&
            new Set(nodes.map(el => firstFamily(el).toLowerCase())).size === 1) {
            add('single-family', 'info', 'Headings and paragraphs use the same computed first family.',
                nodes.map(el => sample(el, {fontFamily: style(el).fontFamily})));
        }
    });
    check('accent-italic-serif', () => {
        const matches = elements.filter(el => {
            const heading = el.parentElement?.closest('h1, h2');
            return heading && style(el).display.startsWith('inline') &&
                style(el).fontStyle === 'italic' && visibleText(el) &&
                firstFamily(el).toLowerCase() !== firstFamily(heading).toLowerCase();
        });
        add('accent-italic-serif', 'warn', 'Italic inline heading accent uses a different family.',
            matches.map(el => sample(el, {fontStyle: style(el).fontStyle,
                fontFamily: style(el).fontFamily,
                headingFamily: style(el.parentElement.closest('h1, h2')).fontFamily})));
    });
    check('gradient-text', () => {
        const matches = elements.filter(el => /gradient\(/.test(style(el).backgroundImage) &&
            /\btext\b/.test(`${style(el).backgroundClip} ${style(el).webkitBackgroundClip}`));
        add('gradient-text', 'warn', 'Text is filled with a gradient.', matches.map(el =>
            sample(el, {backgroundClip: style(el).backgroundClip, backgroundImage: style(el).backgroundImage})));
    });
    check('all-caps-labels', () => {
        // A Korean phrase with an acronym ("AI 티의 정체") is not an uppercase label: require Latin-only text.
        const latinLabel = text => !/[ᄀ-ᇿ㄰-㆏가-힣぀-ヿ一-鿿]/.test(text) &&
            (text.match(/[A-Za-z]/g) || []).length >= 3;
        const matches = textRows.filter(({el, text}) => text.length <= 24 && latinLabel(text) &&
            (style(el).textTransform === 'uppercase' || (/[A-Z]/.test(text) && !/[a-z]/.test(text))));
        if (matches.length >= 4) add('all-caps-labels', 'info', 'Four or more short uppercase labels.',
            matches.map(({el, text}) => sample(el, {textTransform: style(el).textTransform}, text)));
    });

    check('badge-above-h1', () => {
        if (!h1 || !hero) return;
        const index = elements.indexOf(h1);
        let previous = elements.slice(0, index).reverse().find(el => hero.contains(el) && !el.contains(h1));
        while (previous && previous !== hero && !previous.contains(h1)) {
            const box = rect(previous);
            if (box.height <= 40 && Math.min(...radii(previous)) >= box.height / 2 &&
                (hasBackground(previous) || hasBorder(previous)) && box.bottom <= rect(h1).top + 1) {
                add('badge-above-h1', 'warn', 'Small pill immediately precedes the first heading.',
                    [sample(previous, {height: box.height, radii: radii(previous),
                        backgroundColor: style(previous).backgroundColor, borders: borders(previous)})]);
                break;
            }
            previous = previous.parentElement;
        }
    });
    const buttonLike = el => el.matches('button, [role="button"]') ||
        (el.matches('a') && (hasBackground(el) || hasBorder(el) ||
            sides.some(side => number(style(el)[`padding${side}`]) >= 8)));
    check('centered-hero', () => {
        if (!h1 || style(h1).textAlign !== 'center' || rect(h1).top >= innerHeight || rect(h1).bottom <= 0) return;
        const buttons = elements.filter(el => hero.contains(el) && buttonLike(el) &&
            rect(el).top >= rect(h1).bottom - 1 && rect(el).top < innerHeight);
        for (let i = 0; i < buttons.length; i++) {
            for (const b of buttons.slice(i + 1)) {
                const a = buttons[i], ra = rect(a), rb = rect(b), rh = rect(h1);
                const center = (Math.min(ra.left, rb.left) + Math.max(ra.right, rb.right)) / 2;
                if (Math.abs(ra.top - rb.top) <= 20 && Math.abs(center - (rh.left + rh.right) / 2) <= rh.width * 0.1) {
                    add('centered-hero', 'info', 'Centered first-viewport heading with two centered calls to action.',
                        [sample(h1, {textAlign: style(h1).textAlign, top: rh.top,
                            buttons: [sample(a, {left: ra.left, width: ra.width}),
                                sample(b, {left: rb.left, width: rb.width})]})]);
                    return;
                }
            }
        }
    });
    check('icon-card-grid', () => {
        const samples = [];
        for (const parent of elements) {
            const candidates = [...parent.children].filter(visible).filter(el => {
                const icon = [...el.querySelectorAll('svg, img, i, [role="img"], .icon')].find(visible);
                const heading = [...el.querySelectorAll('h1, h2, h3, h4, h5, h6')].find(visible);
                if (!icon || !heading || icon.contains(heading) || heading.contains(icon)) return false;
                const box = rect(icon);
                return box.width <= 64 && box.height <= 64 &&
                    Boolean(icon.compareDocumentPosition(heading) & Node.DOCUMENT_POSITION_FOLLOWING) &&
                    !textRows.some(row => el.contains(row.el) && !icon.contains(row.el) &&
                        (row.el === el || Boolean(row.el.compareDocumentPosition(icon) & Node.DOCUMENT_POSITION_FOLLOWING)));
            });
            const remaining = new Set(candidates);
            for (const card of candidates) {
                if (!remaining.has(card)) continue;
                const r = rect(card);
                const group = [...remaining].filter(other => Math.abs(rect(other).top - r.top) <= 4 &&
                    Math.max(rect(other).width, r.width) / Math.min(rect(other).width, r.width) <= 1.1);
                if (group.length >= 3) {
                    group.forEach(el => {
                        remaining.delete(el);
                        samples.push(sample(el, {top: rect(el).top, width: rect(el).width, siblings: group.length}));
                    });
                }
            }
        }
        add('icon-card-grid', 'warn', 'Aligned sibling cards start with a small icon followed by a heading.', samples);
    });
    check('accent-stripe', () => {
        const matches = elements.filter(el => {
            const widths = borders(el), index = widths.findIndex(w => w > 0);
            const c = index >= 0 && color(style(el)[`border${sides[index]}Color`]);
            return [0, 3].includes(index) && widths[index] >= 2 && widths[index] <= 6 &&
                widths.filter(w => w > 0).length === 1 && c && c[3] > 0 && hsl(c)[1] >= 0.45 &&
                (hasBackground(el) || Math.max(...radii(el)) > 0);
        });
        add('accent-stripe', 'warn', 'Box has a single saturated top or left accent border.', matches.map(el =>
            sample(el, {borders: borders(el), borderColors: sides.map(side => style(el)[`border${side}Color`]),
                backgroundColor: style(el).backgroundColor, radii: radii(el)})));
    });
    check('nested-cards', () => {
        const matches = cards.filter(el => {
            for (let p = el.parentElement; p; p = p.parentElement) if (cards.includes(p)) return true;
            return false;
        });
        add('nested-cards', 'info', 'A padded, rounded card is inside another card.', matches.map(el =>
            sample(el, {radii: radii(el), backgroundColor: style(el).backgroundColor,
                padding: style(el).padding, borderWidth: style(el).borderWidth})));
    });

    check('violet-blue-gradient', () => {
        const matches = elements.filter(el => {
            const bg = style(el).backgroundImage;
            if (!/(?:linear|radial)-gradient\(/.test(bg)) return false;
            const stops = colorTokens(bg).filter(c => c.rgba[3] > 0).map(c => hsl(c.rgba));
            return stops.some(([h, s]) => h >= 250 && h <= 300 && s >= 0.45) &&
                stops.some(([h, s]) => h >= 180 && h <= 235 && s >= 0.45);
        });
        add('violet-blue-gradient', 'warn', 'Gradient combines saturated violet and blue/cyan stops.',
            matches.map(el => sample(el, {backgroundImage: style(el).backgroundImage,
                stops: colorTokens(style(el).backgroundImage).map(c => ({color: c.token, hsl: hsl(c.rgba)}))})));
    });
    check('glow', () => {
        const matches = [];
        for (const el of elements) {
            const css = style(el), box = rect(el), bg = background(el, false);
            const radial = /radial-gradient\(/.test(css.backgroundImage) &&
                Math.max(box.width, box.height) > 300 && bg.rgba && luminance(bg.rgba) < 0.1;
            const shadow = css.boxShadow.split(/,(?![^()]*\))/).some(part => {
                const tokens = colorTokens(part);
                let lengths = part;
                tokens.forEach(c => { lengths = lengths.replace(c.token, ''); });
                const pixels = lengths.match(/-?\d*\.?\d+px/g) || [];
                return number(pixels[2]) >= 40 && tokens.some(c => c.rgba[3] > 0 && hsl(c.rgba)[1] >= 0.25);
            });
            if (radial || shadow) matches.push(sample(el, {backgroundImage: css.backgroundImage,
                boxShadow: css.boxShadow, width: box.width, height: box.height, darkBackground: bg.rgba}));
        }
        add('glow', 'warn', 'Large radial gradient on a dark surface or a broad colored shadow.', matches);
    });
    check('glass', () => {
        const matches = elements.filter(el => /blur\(/.test(style(el).backdropFilter || style(el).webkitBackdropFilter || ''));
        if (matches.length >= 3) add('glass', 'warn', 'Three or more blurred backdrop surfaces.',
            matches.map(el => sample(el, {backdropFilter: style(el).backdropFilter || style(el).webkitBackdropFilter})));
    });
    check('uniform-radius', () => {
        const large = cards.filter(el => Math.min(...radii(el)) >= 16);
        if (cards.length >= 5 && large.length / cards.length >= 0.8) add('uniform-radius', 'info',
            'At least 80% of five or more cards have corner radii of at least 16px.',
            large.map(el => sample(el, {radii: radii(el), totalCards: cards.length, fraction: large.length / cards.length})));
    });

    const hasMotion = el => style(el).animationName.split(',').some(n => n.trim() !== 'none') ||
        (style(el).transitionProperty !== 'none' && style(el).transitionDuration.split(',').some(v => number(v) > 0));
    check('infinite-animation', () => {
        const matches = elements.filter(el => style(el).animationName !== 'none' &&
            style(el).animationIterationCount.split(',').some(value => value.trim() === 'infinite'));
        add('infinite-animation', 'warn', 'Visible elements declare infinitely repeating animations.',
            matches.map(el => sample(el, {animationName: style(el).animationName,
                animationIterationCount: style(el).animationIterationCount, animationDuration: style(el).animationDuration})));
    });
    check('reduced-motion', () => {
        const moving = elements.filter(hasMotion);
        if (!moving.length) return;
        let found = false;
        const unreadable = [], visited = new Set();
        function readSheet(sheet) {
            if (!sheet || visited.has(sheet)) return;
            visited.add(sheet);
            try { readRules(sheet.cssRules); }
            catch (error) { unreadable.push(`${sheet.href || '<inline/adopted>'}: ${error.message}`); }
        }
        function readRules(rules) {
            for (const rule of rules) {
                if (rule.type === CSSRule.MEDIA_RULE && /prefers-reduced-motion/i.test(rule.conditionText)) found = true;
                if (rule.styleSheet) readSheet(rule.styleSheet);
                if (rule.cssRules) readRules(rule.cssRules);
            }
        }
        [...document.styleSheets, ...(document.adoptedStyleSheets || [])].forEach(readSheet);
        if (!found && unreadable.length) skip('reduced-motion',
            `No reduced-motion rule in readable sheets; ${unreadable.length} unreadable stylesheet(s): ${unreadable.join('; ')}`);
        else if (!found) add('reduced-motion', 'warn', 'Motion exists without a readable prefers-reduced-motion media rule.',
            moving.map(el => sample(el, {animationName: style(el).animationName,
                transitionProperty: style(el).transitionProperty, transitionDuration: style(el).transitionDuration})));
    });

    const hangul = /[\u1100-\u11ff\u3130-\u318f\uac00-\ud7af]/;
    check('ko-dash', () => {
        const matches = copyRows.filter(row => hangul.test(row.text) && /[\u2014\u2013\u2015\u2212\uff0d]|\s--?\s/.test(row.text));
        add('ko-dash', 'warn', 'Korean copy contains a dash connector.',
            matches.map(({el, text}) => sample(el, {connectors: text.match(/[\u2014\u2013\u2015\u2212\uff0d]|\s--?\s/g)}, text)));
    });
    function cliches(id, phrases, english = false) {
        const matches = [];
        let count = 0;
        for (const {el, text} of copyRows) {
            const occurrences = {};
            for (const phrase of phrases) {
                const pattern = new RegExp(english ? `\\b${phrase}\\b` : phrase, 'gi');
                const n = (text.match(pattern) || []).length;
                if (n) { occurrences[phrase] = n; count += n; }
            }
            if (Object.keys(occurrences).length) matches.push(sample(el, {occurrences}, text));
        }
        add(id, 'info', 'Stock marketing phrases in visible copy.', matches, count);
    }
    check('ko-cliche', () => cliches('ko-cliche', ['혁신적인', '새로운 차원', '한 단계 업그레이드',
        '지금 바로 경험', '경험해 보세요', '가능성을 열어', '여정', '원활한', '강력한',
        '스마트한 솔루션', '극대화', '차별화된', '최고의 경험', '당신의 비즈니스']));
    check('en-cliche', () => cliches('en-cliche', ['supercharge', 'unlock', 'seamless', 'world-class',
        'revolutionize', 'elevate', 'empower', 'next-generation', 'cutting-edge'], true));
    check('exclaim-cta', () => {
        const matches = elements.filter(el => el.matches('button, a') && /[!！]$/.test(visibleText(el)));
        add('exclaim-cta', 'info', 'Link or button copy ends in an exclamation mark.', matches.map(el =>
            sample(el, {tagName: el.localName})));
    });
    check('not-x-but-y', () => {
        // "프롬프트가 아니라, 도구입니다" / "not just a tool": the framing generated copy reaches for first.
        const ko = /(?:이|가)\s*아니(?:라|고)(?=[,\s])/;
        const en = /\bnot\s+(?:just|only|merely)\b|\b(?:isn't|is not|aren't|are not)\s+(?:just\s+)?(?:a|an|another)\b[^.]*?[,;]\s*(?:it's|it is|they're|we're)\b/i;
        const framed = el => el.matches('h1, h2, h3') ||
            (el.matches('p') && el.previousElementSibling?.matches('h1, h2, h3'));
        // innerText keeps the rendered reading order that inline markup would scramble in visibleText.
        const matches = elements.filter(el => framed(el) && (ko.test(norm(el.innerText)) || en.test(norm(el.innerText))));
        add('not-x-but-y', 'info', 'Heading or lead sentence frames the offer as "not X but Y".',
            matches.map(el => sample(el, {tagName: el.localName})));
    });
    check('two-tone-headline', () => {
        const ownText = el => norm(textRows.filter(row => row.el === el).map(row => row.text).join(' '));
        const matches = elements.filter(el => el.matches('h1, h2') && ownText(el).length >= 2 &&
            [...el.querySelectorAll('*')].some(child =>
                !child.closest('a') && visibleText(child).length >= 2 && style(child).color !== style(el).color));
        add('two-tone-headline', 'info', 'Heading is split into differently colored parts.',
            matches.map(el => sample(el, {color: style(el).color})));
    });
    check('arrow-cta', () => {
        const arrows = /^[→↗↘↓➜➔»›]|[→↗↘↓➜➔»›]$/;
        const matches = elements.filter(el => el.matches('a, button') && arrows.test(norm(el.innerText)));
        add('arrow-cta', 'info', 'Link or button text starts or ends with an arrow glyph.',
            matches.map(el => sample(el, {tagName: el.localName})));
    });
    check('speech-level-mix', () => {
        const matches = [], totals = {yo: 0, nida: 0};
        for (const {el, text} of copyRows) {
            if (!hangul.test(text)) continue;
            const yo = (text.match(/요\s*[.?!](?=\s|$|["'”’])/g) || []).length;
            const nida = (text.match(/니다\s*[.?!](?=\s|$|["'”’])/g) || []).length;
            totals.yo += yo; totals.nida += nida;
            if (yo || nida) matches.push(sample(el, {yo, nida}, text));
        }
        const total = totals.yo + totals.nida;
        if (total && totals.yo / total >= 0.2 && totals.nida / total >= 0.2) {
            add('speech-level-mix', 'info', `Korean sentence endings mix 요 (${totals.yo}) and 니다 (${totals.nida}).`,
                matches.map(s => ({...s, computed: {...s.computed, totals}})), total);
        }
    });
    check('emoji-icons', () => {
        const matches = elements.filter(el => el.matches('h1, h2, h3, h4, h5, h6, nav a, [role="navigation"] a, li') &&
            /^(?:\p{Extended_Pictographic}|\p{Regional_Indicator}|[#*0-9]\ufe0f?\u20e3)/u.test(visibleText(el)));
        add('emoji-icons', 'warn', 'Heading, navigation link, or list item starts with an emoji.',
            matches.map(el => sample(el, {tagName: el.localName})));
    });

    check('overflow-x', () => {
        const root = document.documentElement;
        if (root.scrollWidth <= root.clientWidth + 1) return;
        const offending = elements.filter(el => rect(el).right > root.clientWidth + 1 || rect(el).left < -1)
            .sort((a, b) => rect(b).width - rect(a).width);
        add('overflow-x', 'error', `Document width ${root.scrollWidth}px exceeds viewport ${root.clientWidth}px.`,
            (offending.length ? offending : [root]).map(el => sample(el, {left: rect(el).left, right: rect(el).right,
                width: rect(el).width, scrollWidth: root.scrollWidth, clientWidth: root.clientWidth})));
    });
    check('contrast', () => {
        const matches = [], reasons = new Map();
        function unavailable(reason, el) {
            if (!reasons.has(reason)) reasons.set(reason, []);
            reasons.get(reason).push(selector(el));
        }
        for (const {el, text} of textRows) {
            const css = style(el);
            let special = null;
            for (let p = el; p; p = p.parentElement) {
                const s = style(p);
                if (number(s.opacity) < 1 || s.filter !== 'none' || s.mixBlendMode !== 'normal' ||
                    (s.backdropFilter && s.backdropFilter !== 'none')) {
                    special = 'opacity, filter, or blending prevents reliable ancestor-only contrast'; break;
                }
            }
            const bg = background(el);
            if (special || bg.reason) { unavailable(special || bg.reason, el); continue; }
            const foreground = color(css.webkitTextFillColor || css.color);
            if (!foreground || foreground[3] === 0) { unavailable('transparent or unresolved text fill', el); continue; }
            const rgb = over(foreground, bg.rgba), l1 = luminance(rgb), l2 = luminance(bg.rgba);
            const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
            const size = number(css.fontSize), weight = number(css.fontWeight);
            const threshold = size >= 24 || (size >= 18.66 && weight >= 700) ? 3 : 4.5;
            if (ratio < threshold) matches.push(sample(el, {color: css.color,
                textFillColor: css.webkitTextFillColor, background: bg.rgba,
                fontSize: css.fontSize, fontWeight: css.fontWeight,
                ratio: Math.round(ratio * 100) / 100, threshold}, text));
        }
        add('contrast', 'warn', 'Text has low contrast against its ancestor-derived background.', matches);
        for (const [reason, selectors] of reasons) skip('contrast',
            `${selectors.length} text element(s): ${reason}; ${selectors.slice(0, 5).join(', ')}`);
    });
    check('tap-target', () => {
        if (innerWidth > 480) return;
        const matches = elements.filter(el => {
            if (!el.matches('a, button')) return false;
            if (el.matches('a') && style(el).display === 'inline' && !buttonLike(el)) {
                const block = copyRows.find(row => row.el.contains(el) && row.el !== el);
                if (block && block.text.length > visibleText(el).length) return false;
            }
            return rect(el).width < 44 || rect(el).height < 44;
        });
        add('tap-target', 'warn', 'Mobile link or button is smaller than 44px in one or both dimensions.',
            matches.map(el => sample(el, {width: rect(el).width, height: rect(el).height, display: style(el).display})));
    });
    check('img-dimensions', () => {
        const matches = elements.filter(el => el.matches('img') &&
            (!el.hasAttribute('width') || !el.hasAttribute('height')) &&
            (!style(el).aspectRatio || style(el).aspectRatio === 'auto'));
        add('img-dimensions', 'info', 'Image lacks a complete width/height attribute pair and CSS aspect-ratio.',
            matches.map(el => sample(el, {src: el.currentSrc || el.src, width: el.getAttribute('width'),
                height: el.getAttribute('height'), aspectRatio: style(el).aspectRatio})));
    });
    check('img-alt', () => {
        const matches = elements.filter(el => el.matches('img') && !el.hasAttribute('alt'));
        add('img-alt', 'warn', 'Image has no alt attribute (empty alt is allowed).',
            matches.map(el => sample(el, {src: el.currentSrc || el.src, alt: null})));
    });
    const paragraphs = elements.filter(el => el.matches('p') && visibleText(el));
    const fontTargets = [h1, headings.find(el => el.matches('h2')),
        paragraphs.find(el => hangul.test(visibleText(el))) || paragraphs[0]].filter(Boolean)
        .map(el => sample(el, {fontFamily: style(el).fontFamily, firstFamily: firstFamily(el)}));
    return {findings, skipped, fontTargets};
}"""

GENERIC_FAMILIES = {
    "serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui",
    "ui-serif", "ui-sans-serif", "ui-monospace", "ui-rounded", "emoji",
    "math", "fangsong",
}
SEVERITIES = {"info": 0, "warn": 1, "error": 2}


class AuditLoadError(Exception):
    """Target, browser, output, or navigation failure, rather than a finding."""


def target_url(target: str) -> str:
    """Resolve Windows/POSIX paths without interpreting drive letters as schemes."""
    if re.match(r"^https?://", target, re.I):
        if not urlsplit(target).hostname:
            raise AuditLoadError(f"Invalid URL: {target}")
        return target
    if target.lower().startswith("file://"):
        parts = urlsplit(target)
        path = url2pathname(parts.path)
        if parts.netloc and parts.netloc != "localhost":
            path = f"//{parts.netloc}{path}"
        if not Path(path).is_file():
            raise AuditLoadError(f"File does not exist: {unquote(target)}")
        return target
    path = Path(target).expanduser().resolve()
    if not path.is_file():
        raise AuditLoadError(f"File does not exist: {path}")
    return path.as_uri()


def _font_key(value: str) -> str:
    return re.sub(r"\s+", "", value).casefold()


def font_fallback(page, targets: list[dict], width: int) -> tuple[list, list]:
    """Compare dominant glyph-count font per sampled node using Chrome's CDP."""
    samples, skipped = [], []
    candidates = []
    for target in targets:
        declared = target["computed"]["firstFamily"]
        if declared.casefold() in GENERIC_FAMILIES:
            skipped.append({"id": "font-fallback", "width": width,
                            "reason": f"{target['selector']}: generic family {declared!r} has no concrete font to compare."})
        else:
            candidates.append(target)
    if not targets:
        skipped.append({"id": "font-fallback", "width": width,
                        "reason": "No visible h1, h2, or paragraph to measure."})
    if not candidates:
        return [], skipped
    session = None
    try:
        session = page.context.new_cdp_session(page)
        session.send("DOM.enable")
        root = session.send("DOM.getDocument", {"depth": 0})["root"]["nodeId"]
        session.send("CSS.enable")
        for target in candidates:
            try:
                node = session.send("DOM.querySelector", {"nodeId": root, "selector": target["selector"]})["nodeId"]
                if not node:
                    raise RuntimeError("element no longer exists")
                fonts = session.send("CSS.getPlatformFontsForNode", {"nodeId": node})["fonts"]
                fonts = [font for font in fonts if font.get("glyphCount", 0) > 0]
                if not fonts:
                    raise RuntimeError("CDP returned no rendered glyphs")
                # Multiple faces of one family count together before dominance.
                families = {}
                for font in fonts:
                    key = _font_key(font["familyName"])
                    item = families.setdefault(key, {"familyName": font["familyName"], "glyphCount": 0})
                    item["glyphCount"] += font["glyphCount"]
                dominant = max(families.values(), key=lambda font: font["glyphCount"])
                declared = target["computed"]["firstFamily"]
                if not _font_key(dominant["familyName"]).startswith(_font_key(declared)):
                    samples.append({**target, "computed": {**target["computed"],
                                    "dominantFamily": dominant["familyName"], "platformFonts": fonts}})
            except Exception as exc:
                skipped.append({"id": "font-fallback", "width": width,
                                "reason": f"{target['selector']}: CDP font measurement unavailable: {exc}"})
    except Exception as exc:
        skipped.append({"id": "font-fallback", "width": width,
                        "reason": f"CDP font measurement unavailable: {exc}"})
    finally:
        if session is not None:
            try:
                session.detach()
            except Exception:
                pass
    findings = []
    if samples:
        findings.append({"id": "font-fallback", "severity": "error", "width": width,
                         "message": "Dominant rendered font differs from the declared first family.",
                         "count": len(samples), "samples": samples[:5]})
    return findings, skipped


def markdown_report(report: dict) -> str:
    lines = ["# Rendered-page audit", "", f"Target: {report['target']}",
             f"Generated: {report['generated_at']}",
             f"Widths: {', '.join(map(str, report['widths']))}", "",
             ", ".join(f"{report['counts'][level]} {level}" for level in ("error", "warn", "info")),
             "", "Findings are review evidence, not a verdict. Counts are finding records per width.",
             "Checks cover the top document at load; geometry, copy, and ancestor-background contrast are heuristic.",
             ""]
    if not report["findings"]:
        lines.extend(["No findings recorded. Check skipped coverage below.", ""])
    for finding in report["findings"]:
        lines.extend([f"## {finding['severity'].upper()}: {finding['id']} ({finding['width']}px)", "",
                      f"{finding['message']} Matches: {finding['count']}.", "", "```json",
                      json.dumps(finding["samples"], ensure_ascii=False, indent=2), "```", ""])
    fp = report.get("fingerprint")
    if fp:
        accents = " ".join(item["hex"] for item in fp["accents"][:3]) or "none"
        lines.extend([f"## Fingerprint ({fp.get('width')}px)", "",
                      f"- ground {fp['ground']['hex']}, ink {fp['ink']['hex']}, accents {accents}, "
                      f"chromatic area {fp['chromaticShare']}",
                      f"- type scale {fp['scale']} (largest {fp['largestSize']}px over body {fp['bodySize']}px), "
                      f"display {fp['display'] or 'none'}",
                      f"- habits: {', '.join(fingerprint.tics(fp)) or 'none'}", ""])
    lines.extend(["## Skipped", ""])
    if report["skipped"]:
        for item in report["skipped"]:
            reason = item["reason"].replace("\n", " ").replace("\r", " ")
            lines.append(f"- **{item['id']} ({item['width']}px):** {reason}")
    else:
        lines.append("None.")
    lines.extend(["", "## Screenshots", ""])
    for width, path in report["screenshots"].items():
        lines.append(f"- [{width}px](<{Path(path).as_uri()}>)")
    return "\n".join(lines) + "\n"


def run_audit(browser, target: str, widths=(1440, 390), out="./audit-out", timeout=30, ledger=None) -> dict:
    """Audit with a caller-owned browser; each width gets an isolated context."""
    url = target_url(str(target))
    output = Path(out).resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = {"target": url, "generated_at": datetime.now(timezone.utc).isoformat(),
              "widths": list(widths), "findings": [], "skipped": [],
              "counts": {"error": 0, "warn": 0, "info": 0}, "screenshots": {}}
    for width in widths:
        context = browser.new_context(viewport={"width": width, "height": 900}, device_scale_factor=1)
        try:
            page = context.new_page()
            page.set_default_timeout(timeout * 1000)
            diagnostics = []

            def diagnostic(text, **values):
                diagnostics.append({"selector": None, "text": str(text)[:500], "computed": values})

            def on_console(message):
                location = urlsplit((message.location or {}).get("url") or "").path
                if message.type == "error" and location != "/favicon.ico":
                    diagnostic(message.text, kind="console", location=message.location)

            def on_response(response):
                # Chrome asks every served page for /favicon.ico; a missing one is not a page defect.
                if response.status >= 400 and urlsplit(response.url).path != "/favicon.ico":
                    diagnostic(f"HTTP {response.status}: {response.url}",
                               kind="http", url=response.url, status=response.status)

            page.on("console", on_console)
            page.on("pageerror", lambda error: diagnostic(error, kind="pageerror"))
            page.on("requestfailed", lambda request: diagnostic(
                request.failure, kind="requestfailed", url=request.url, method=request.method))
            page.on("response", on_response)
            try:
                response = page.goto(url, wait_until="load", timeout=timeout * 1000)
                if response is not None and response.status >= 400:
                    raise AuditLoadError(f"HTTP {response.status} loading {url}")
                # evaluate promises do not obey Playwright's default timeout.
                page.evaluate("""ms => Promise.race([
                    document.fonts.ready.then(() => true),
                    new Promise((_, reject) => setTimeout(() => reject(new Error('Font readiness timed out')), ms))
                ])""", timeout * 1000)
                page.wait_for_timeout(250)
            except Exception as exc:
                raise AuditLoadError(f"Cannot load {url} at {width}px: {exc}") from exc
            result = page.evaluate(DOM_AUDIT)
            report["findings"].extend({**item, "width": width} for item in result["findings"])
            report["skipped"].extend({**item, "width": width} for item in result["skipped"])
            font_findings, font_skipped = font_fallback(page, result["fontTargets"], width)
            report["findings"].extend(font_findings)
            report["skipped"].extend(font_skipped)
            screenshot = output / f"{width}.png"
            # Preserve motion in the evidence; screenshot capture is also bounded.
            page.screenshot(path=str(screenshot), full_page=True, timeout=timeout * 1000)
            report["screenshots"][str(width)] = str(screenshot)
            if width == max(widths):
                try:
                    measured = fingerprint.measure(page, timeout)
                    report["fingerprint"] = measured
                    report["findings"].extend({**item, "width": width}
                                              for item in fingerprint.findings(measured, ledger or []))
                except Exception as exc:
                    report["skipped"].append({"id": "generated-look", "width": width,
                                              "reason": f"Fingerprint measurement unavailable: {exc}"})
            if diagnostics:
                report["findings"].append({"id": "console-errors", "severity": "warn", "width": width,
                                           "message": "Console errors, uncaught exceptions, or failed load requests.",
                                           "count": len(diagnostics), "samples": diagnostics[:5]})
        finally:
            context.close()
    for finding in report["findings"]:
        report["counts"][finding["severity"]] += 1
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "report.md").write_text(markdown_report(report), encoding="utf-8")
    return report


def parse_widths(value: str) -> list[int]:
    try:
        widths = [int(part.strip()) for part in value.split(",")]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("widths must be comma-separated positive integers") from exc
    if not widths or any(width <= 0 for width in widths):
        raise argparse.ArgumentTypeError("widths must be comma-separated positive integers")
    return list(dict.fromkeys(widths))


def positive_timeout(value: str) -> float:
    try:
        timeout = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("timeout must be a positive number of seconds") from exc
    if not math.isfinite(timeout) or timeout <= 0:
        raise argparse.ArgumentTypeError("timeout must be a positive number of seconds")
    return timeout


def main(argv=None, *, browser=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="HTTP(S) URL or local HTML path")
    parser.add_argument("--widths", type=parse_widths, default=[1440, 390])
    parser.add_argument("--out", default="./audit-out")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown")
    parser.add_argument("--fail-on", choices=("error", "warn"), default="error")
    parser.add_argument("--timeout", type=positive_timeout, default=30)
    parser.add_argument("--ledger", type=Path, help="design ledger whose recent fingerprints the page is compared with")
    args = parser.parse_args(argv)
    try:
        url = target_url(args.target)
        ledger = fingerprint.read_ledger(args.ledger.expanduser()) if args.ledger else []
        if browser is not None:
            report = run_audit(browser, url, args.widths, args.out, args.timeout, ledger)
        else:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as playwright:
                chrome = playwright.chromium.launch(channel="chrome", headless=True)
                try:
                    report = run_audit(chrome, url, args.widths, args.out, args.timeout, ledger)
                finally:
                    chrome.close()
        print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else markdown_report(report), end="\n")
        threshold = SEVERITIES[args.fail_on]
        return int(any(SEVERITIES[item["severity"]] >= threshold for item in report["findings"]))
    except Exception as exc:
        print(f"audit: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    # Windows redirected stdout may otherwise use a legacy code page.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())

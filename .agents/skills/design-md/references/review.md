# Reviewing a landing page

Read when auditing a build, reviewing another model's page, rewriting copy, or planning a blind test.

## Rendered audit

`python scripts/audit.py <url-or-file> --widths 1440,390 --out <dir> [--fail-on warn]` loads the page in installed Chrome and writes `report.json`, `report.md` and full-page screenshots per width. Findings are evidence with samples (selector, text, computed values), not a verdict.

| Severity | Checks | What to do |
|---|---|---|
| error | `font-fallback`, `overflow-x` | Fix. A fallback means the site does not show the licensed face DESIGN.md names. |
| warn | `font-generic`, `accent-italic-serif`, `gradient-text`, `badge-above-h1`, `icon-card-grid`, `accent-stripe`, `violet-blue-gradient`, `glow`, `glass`, `infinite-animation`, `reduced-motion`, `ko-dash`, `emoji-icons`, `contrast`, `tap-target`, `img-alt`, `console-errors`, `generated-look`, `near-recent` | Fix, or cite the DESIGN.md reason when it is a deliberate choice of this direction. `generated-look` and `near-recent` come from the measured render (fingerprint.py): fix them by changing the color source or the decoration habits, not by nudging values. |
| info | `single-family`, `all-caps-labels`, `centered-hero`, `nested-cards`, `uniform-radius`, `ko-cliche`, `en-cliche`, `exclaim-cta`, `not-x-but-y`, `two-tone-headline`, `arrow-cta`, `speech-level-mix`, `img-dimensions` | Read the samples; several infos on one page usually mean the template skeleton is back. |

`skipped` entries (for example unreadable cross-origin stylesheets, or text under `opacity` or `mix-blend-mode` for contrast) mean the check did not run. Report them; do not count them as clean. Geometry, contrast (ancestor backgrounds only) and copy checks are heuristics.

Audit a served page, not `file://`: a `<link rel="preload" ... crossorigin>` font is blocked by CORS on `file://` and shows up as `console-errors` and a missing face. From the site folder, `python -m http.server 8000 --bind 127.0.0.1`, then audit `http://127.0.0.1:8000/`.

## Tells the audit cannot judge

- The section skeleton is the default one regardless of the chosen narrative.
- Nothing on the page could only belong to this business: swap the name and it still works.
- Every section has the same spacing, so nothing groups.
- Images disagree in light direction or look like different shoots.
- Motion that exists only because it can: every element fading up on scroll, cards lifting that are not clickable.
- Copy promises without who, what or when.
- A dark terminal block, a decorative bar chart or a mono "01 / label" eyebrow standing in for evidence the page does not have.

## Copy

Replace claims with facts from the material:

| Generated | Rewritten | What changed |
|---|---|---|
| 비즈니스의 가능성을 확장하세요 | 견적서 작성부터 입금 확인까지 한곳에서 | who does what |
| 매일 아침, 특별한 빵을 경험해 보세요 | 식빵은 7시 30분, 소금빵은 11시에 나옵니다 | a real time instead of an adjective |
| 전문 의료진이 최상의 케어를 제공합니다 | 초진은 30분을 잡고, 검사 결과는 당일 원장이 직접 설명합니다 | a procedure instead of a promise |

Korean copy rules: no em/en dashes or spaced hyphen connectors between clauses (use a period, comma or parentheses), one speech level per page, no stock phrases (혁신적인, 새로운 차원, 한 단계 업그레이드, 지금 바로 경험해 보세요, 여정), buttons that name the action without exclamation marks, and headlines checked at 390px for a single syllable left on the last line.

## Cross-model review

When Claude implemented, ask Codex (and the reverse) with the brief, DESIGN.md, the screenshots, the audit report and the URL or files:

```text
Review this landing page against the brief, DESIGN.md and the screenshots. Report violations only, each with
location and evidence: sections or order that contradict direction.narrative, type or color outside the
tokens, generated images used where originals are required, copy claims without material, differences
from DESIGN.md, audit findings not fixed or justified. Do not propose a new visual direction.
```

## Designer polish skills

The skills recommended in the source post are useful for a final polish pass when installed: `npx skills add jakubkrehel/skills` (`/better-interface` combines layout, typography, OKLCH color, accessibility, UI writing and polish reviews) and `npx skills add emilkowalski/skill` (motion and interface polish). Run them after the direction is implemented and tell them which choices DESIGN.md records as intentional. Generic all-in-one design skills tend to make results look more generated, not less.

## Blind test

Only people outside the project can say whether a page reads as generated.

1. Mix 3 pages from this workflow with 3 human-made sites of the same industry and similar information (ordinary real sites, not award winners), in random order.
2. Recruit people close to the target customer and, separately, designers.
3. For each page ask: 5-second understanding (what is offered and for whom), 30-second trust (what feels specific, what feels doubtful, where is the next action), AI guess on a 1 to 5 scale with the concrete reason, and, with logos hidden, whether our recent pages look like one template.
4. Pass when the AI guess is not higher than the human set while understanding and trust hold, and our pages are not grouped as one template. Feed the stated reasons back into the tells and the direction lists. Small samples show tendencies only; never conclude "no one can tell".

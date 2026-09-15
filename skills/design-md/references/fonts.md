# Fonts for landing pages

Read before choosing faces for a client site, adding a catalog entry, or converting Photoshop type settings to CSS.

## Strategy

- Decide the Korean headline face first. Swapping a Latin display font while the Hangul headline stays Pretendard does not change the page's impression.
- Split roles: a display face for headlines and a text face for reading, or one family with strong weight contrast (Paperlogy, S-Core Dream). Two similar sans families look like a mistake. Rarely use more than three families.
- Pretendard, Noto Sans KR and Gmarket Sans are good faces. The tell is repetition: one family, the same weights, the same headline size and column width on every page. Keep them as text faces under a characterful display face, or state the reason.
- Below 18px keep weight 400 or more; thin weights are for display sizes of 28px and up.
- Latin accents (Bebas Neue for numbers, Newsreader for a newspaper feel) are optional and should serve the world, not decorate.

## License rules the scripts enforce

`references/fonts.json` records for each face: `license`, `licenseUrl`, `webEmbedding`, `modify`, `verified` and the quoted `evidence`.

| Situation | Rule |
|---|---|
| `webEmbedding: false` (KoPubWorld) | Photoshop comps, images and print only. `fonts.py fetch` skips web files and the fork lint reports an error if typography uses it. KoPub requires separate approval to embed on a server. |
| `modify: false` (S-Core Dream) | Serve the distributed OTF/TTF unchanged: no subsetting, no woff2 conversion, keep the copyright notice. Expect larger files. |
| Adobe Fonts (desktop sync) | Fine for Photoshop and for rasterized images (PNG, JPEG, PDF with embedded outlines). On the web only through an Adobe web project embed code; self-hosting the files is prohibited, and a client site needs the client's own Creative Cloud subscription. Do not ship them from `assets/fonts`. |
| Paid foundry fonts (Sandoll, Yoon and others) | Allowed only when the user supplies a license that covers web embedding for this site. Record license name, scope and date in DESIGN.md `fonts`. |
| "Commercial free" wording | Does not by itself allow web embedding, subsetting, modification or redistribution. Read the license text; keep it next to the files. |
| Sources that disagree (Jalnan) | The embedded license text permits modification while the official PDF guide forbids redistributing modified files. Until the distributor resolves it, the catalog keeps `modify: false` and the fetch serves the original OTF. |

Licenses change. `verified` is the date the license page was read; re-read it before a client delivery and update the date.

## Adding a font to the catalog

1. Read the license on the official distribution page or the license file inside the download, not a blog summary. Summaries have been wrong in both directions (one list marked KoPubWorld web-embeddable; a fetch summary called Gmarket Sans unmodifiable although its page grants modification).
2. Quote the sentence that decides web use and modification in `evidence`.
3. Add a `source` the fetcher can reproduce: `google` (verified from google/fonts METADATA.pb at fetch time), `npm` (jsDelivr), `zip` (official archive, nested zips allowed), `raw` (file URLs) or `manual`.
4. Fetch it into a temporary folder and compare the declared weights with the file names. Distributions lie: Gmarket Sans Medium declares 400, MaruBuri ExtraLight declares 300, NanumSquare Neo Light declares 350, each S-Core Dream weight is its own family. Record the intended weight per file stem in `source.weightMap`, or `--weights` will select the wrong files or none.
5. Check `ps-names` and the rendered weights, then add pairings that use it.

Two things the fetch cannot fix for you:

- **A distribution that ships no license text.** Several Korean archives (MaruBuri, NanumSquare Neo, Gmarket Sans, Jalnan, S-Core Dream) contain only font files. The fetch then writes `LICENSE-EVIDENCE.txt` with the quoted evidence and saves the license page as `LICENSE-PAGE.html`. For an OFL face, also put the upstream `OFL.txt` next to the files before you redistribute them; `source.licenseUrlRaw` downloads it when the project publishes one.
- **A variable file.** `ps-names` marks it: Photoshop opens the default instance, so a comp at weight 700 needs the weight axis set by hand or a static file, while the web build uses the variable file's range. When an archive ships both, the fetch keeps the static files.

## Same files in Photoshop and on the web

1. `fonts.py fetch` puts desktop files (`desktop/`) and web files (`web/`) from the same distribution side by side, with `fonts.lock.json` (URLs, SHA-256, license) and a combined `fonts.css`.
2. `fonts.py install` copies the desktop files into the user font folder (Windows registry entry included). Photoshop reads fonts at launch; `photoshop_comp.py --restart` restarts it only when no document is open.
3. If Adobe Fonts activates a family with the same PostScript name, deactivate it so Photoshop uses the installed file.
4. `fonts.py ps-names` gives the PostScript names to put in the comp spec.

Converting Photoshop settings to CSS (documents at 72 ppi, type units in pixels):

- Tracking is in 1/1000 em: tracking `-20` is `letter-spacing: -0.02em`.
- Leading in px divided by font size gives the unitless `line-height` (84 / 64 = 1.3125).
- Paragraph box width in px becomes the column `max-width`; check line breaks in the browser because renderers differ.

In the build use `font-synthesis: none` so the browser does not fake missing weights, preload only the display face's first-screen weight, take screenshots after `document.fonts.ready`, and confirm in DevTools Rendered Fonts (or `audit.py` `font-fallback`) that Hangul, numbers and punctuation did not fall back. Google Fonts entries arrive as unicode-range slices, so the browser downloads only the syllables a page uses. The HTML is the final reference; the comp sets direction and proportions.

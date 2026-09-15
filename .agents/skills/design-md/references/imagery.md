# Images: Codex image generation and the retouching pass

Read before generating or processing images for a page.

## What to generate and what not to

Generate: background plates for compositing, scenes and places that set the mood, textures, abstract material studies, reference comps for light and color.

Use originals, never generated: the product's exact form and packaging, real UI and dashboards, any person presented as a customer, staff member, doctor or reviewer, before/after results, awards, certificates, storefronts presented as the actual shop, numbers and charts presented as evidence. A reference image does not make the model preserve a product's structure.

## Command

Use the codex-cli skill's host-safe form and pin the model:

```bash
codex exec -m gpt-6-astra -s danger-full-access -c mcp_servers='{}' \
  "<prompt> ... Resize the result to 2400x1600 and save to <project>/images/raw/<name>-01.png" \
  -i <project>/images/ref/<real-photo>.jpg
```

Prompt first and `-i` last: `-i` is variadic and swallows following arguments. The tool often returns a different size than requested, so ask for the resize and check the file. Generate several candidates for the same slot and choose the least polished one that fits.

## Prompt skeleton

Write prompts in English. Name physical facts, not quality adjectives.

```text
Generate one photograph for a landing page section.
Use: <background plate for a real product photo | scene | texture>.
Subject: <the real place or object, based on the reference>.
Reference A: use only <camera height and margin placement>. Reference B: use only <wall material and saturation>.
Camera: <35mm film camera, 40mm lens, Kodak Portra 400, slight underexposure>.
Light: <single window on the left, low warm sun around 4 pm, hard shadow falling right>.
Framing: <subject on the right third, top edge cut off, empty wall on the left for the headline>.
Texture: <visible film grain, faint dust, natural surface wear>.
Do not include: any text, letters, logos, UI, faces looking at the camera, studio gradient backdrop,
symmetrical composition, glossy 3D render look, bokeh balls, neon or violet light.
```

Per image treatment, start from `imagePrompts` in `directions.json`. Narrow follow-ups keep what worked: "keep the light direction and materials, only move the camera back". Avoid stacking `award-winning`, `cinematic`, `8k`, `masterpiece` or "make it not look AI"; they give no criterion and pull toward glossy advertising.

Why generated images look generated: skin without pores, pixels without sensor noise, light without a source, identical catchlights, cut-out edges, perfect symmetry, garbled letters, a different light direction in every image on the page.

## Retouching pass

A raw generation is rarely the asset. Work the file in an image editor before it goes on the page; the steps below name Photoshop tools, and any editor with the same operations will do.

| Step | How |
|---|---|
| Clean defects | Clone stamp, patch and remove tool for hands, repeated patterns and letter-like marks. Generative fill reintroduces generated texture; keep it to small areas. |
| Composite real products | Match shadow direction and color temperature to the plate; paint the contact shadow on a multiply layer. |
| Unify the set | Put all images of the page side by side; match exposure, white balance and black level. |
| Grade into the palette | Curves or Color Lookup adjustment layers so photos sit inside the DESIGN.md colors. Match the saturation the direction calls for: a broadcast, packaging or market-sign world wants it high, and a default "slightly desaturated, warm" grade is the generated look again. |
| Grain | Only when the image treatment calls for it, the same size on every image. Camera Raw grain around amount 15 to 25, size 20 to 30 is a starting point. Grain does not fix wrong structure. |
| Crop per breakpoint | Separate desktop and mobile crops that fit the image boxes the page actually uses; move the subject off center. |
| Export | WebP or JPEG at twice the displayed size; keep the layered original and the raw generation. |

## Provenance and advertising limits

- The goal is design quality, not hiding where an image came from. Do not strip C2PA or other provenance data on purpose. OpenAI documents C2PA metadata and additional watermark signals on generated images.
- Korea's AI Basic Act (in force 2026-01-22, Article 31) places labeling duties on businesses that provide AI products or services, with at least a year of guidance period; a business that only uses generated images in its own marketing is generally described as a user, not the duty holder. Realistic synthetic people or events that could be mistaken for real need a visible label.
- The Fair Labeling and Advertising Act still applies: generated people shown as real customers or experts, or invented results, can be deceptive advertising. Medical, food and drug advertising is stricter; use only real, consented photographs for people and outcomes there.
- This is a summary of public sources, not legal advice. Check the rules of the client's industry before publishing.

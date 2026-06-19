# kairos-extract

**Kind:** engine brick · **NAME:** `extract` · depends on `kairos-core` + `kairos-ocr`

Zonal/template field extraction. For each configured field it locates a region
(by page-ratio box), crops it at several margins, OCRs each crop (via the injected
`ocr` brick), and **reconciles** the readings: keep those matching the field's
`format`, pick the highest confidence, cast to the declared type.

- **Input:** `list[ {"path", "name"} ]` (from `source`); supports PDF (rasterized) and images.
- **Output:** `list[ {"source", "fields": {name: {value, confidence, format_matched, raw, margin_used}}} ]`.
- **Injects:** the `ocr` brick (`INJECTS = {"ocr": "ocr"}`) — install an `ocr` brick and give it a config section.

## Install
```bash
pip install kairos-core kairos-extract kairos-ocr
```

## Config
Engine brick: the `extract:` section *is* its settings.

```yaml
ocr: {impl: tesseract, params: {cmd: "...", psm: 7}}   # required: extract injects this

extract:
  pdf_dpi: 200                  # rasterization DPI for PDF inputs (default 200)
  pdf_page: 0                   # default page for fields (0-based)
  canonical: {long_side_px: 2200}   # reference unit for `margins` (image is NOT resized)
  fields:
    - name: invoice_number      # field name (becomes the output key)
      type: string              # string | int | money | date
      box: [0.75, 0.14, 0.18, 0.02]   # [x, y, w, h] as ratios 0..1 of the page
      margins: [2, 6, 10]       # canonical px tried around the box (reconciliation)
      format: 'INV-\d+'         # regex; readings must fullmatch to be kept
      page: 0                   # optional: PDF page for THIS field (multi-page docs)
      chars: '0123456789-'      # optional: restrict OCR to these characters
```

### Field parameters
| key | meaning |
|---|---|
| `name` | output key |
| `type` | `string` / `int` / `money` / `date` (controls casting) |
| `box` | `[x, y, w, h]` ratios 0..1 (shorthand for a `fixed` locator) |
| `margins` | list of canonical-px expansions tried; reconciliation picks the best |
| `format` | regex the reading must fullmatch (the real correctness signal) |
| `page` | (optional) PDF page index for this field; defaults to `pdf_page` |
| `chars` | (optional) per-field OCR character whitelist (e.g. avoid 0/O confusion) |

**Reconciliation rule:** across the margins, keep readings matching `format`, pick the
highest confidence, cast to `type`. If none match, the highest-confidence raw reading is
kept with `format_matched=false` (so `validate` can flag it). Boxes are ratios, so the
same config works across DPIs/scan sizes (the page is not resampled).

"""kairos-extract unit test — zonal extract + reconciliation + resolution independence.

Uses the synthetic OCR (injected via wire) so it runs offline.
"""
from __future__ import annotations

from pathlib import Path

from _harness import harness

import textgen
from kairos_core import wire

import kairos_extract as extract
import kairos_ocr as ocr

test = harness(__name__)
TMP = Path(__file__).resolve().parent / "_tmp"

LAYOUT = {"invoice_number": (0.10, 0.08), "date": (0.10, 0.14), "total": (0.62, 0.82)}
VALUES = {"invoice_number": "INV-000123", "date": "2026-06-18", "total": "1234.56"}
INVOICE_CHARSET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-./:#,$"


def _boxes():
    return {n: (x - 0.01, y - 0.01, 0.26, 0.035) for n, (x, y) in LAYOUT.items()}


def _config():
    b = _boxes()
    return extract.CONFIG_MODEL.model_validate({"canonical": {"long_side_px": 1500}, "fields": [
        {"name": "invoice_number", "type": "string", "box": list(b["invoice_number"]),
         "margins": [2, 5, 8], "format": r"INV-\d{6}"},
        {"name": "date", "type": "date", "box": list(b["date"]),
         "margins": [2, 5, 8], "format": r"\d{4}-\d{2}-\d{2}"},
        {"name": "total", "type": "money", "box": list(b["total"]),
         "margins": [2, 5, 8], "format": r"\d+\.\d{2}"},
    ]})


def _wire(cfg):
    ocr_cfg = ocr.CONFIG_MODEL.model_validate(
        {"impl": "synthetic", "params": {"font_size": 44, "charset": INVOICE_CHARSET}})
    return wire({"extract": extract, "ocr": ocr}, {"extract": cfg, "ocr": ocr_cfg})["extract"]


def _render(path, size):
    return textgen.save(
        textgen.render_invoice(VALUES, LAYOUT, size=size, font_size=int(0.029 * size[0])), path)


@test
def test_reads_and_reconciles():
    TMP.mkdir(exist_ok=True)
    _render(TMP / "a.png", (1500, 2100))
    out = _wire(_config()).run([{"path": str(TMP / "a.png"), "name": "a.png"}])[0]["fields"]
    assert out["invoice_number"]["value"] == "INV-000123", out["invoice_number"]
    assert out["invoice_number"]["format_matched"] is True
    assert out["date"]["value"] == "2026-06-18", out["date"]
    assert out["total"]["value"] == 1234.56, out["total"]


@test
def test_resolution_independence():
    TMP.mkdir(exist_ok=True)
    _render(TMP / "lo.png", (1500, 2100))
    _render(TMP / "hi.png", (2250, 3150))
    bound = _wire(_config())
    lo = bound.run([{"path": str(TMP / "lo.png"), "name": "lo"}])[0]["fields"]
    hi = bound.run([{"path": str(TMP / "hi.png"), "name": "hi"}])[0]["fields"]
    for n in VALUES:
        assert lo[n]["value"] == hi[n]["value"], (n, lo[n], hi[n])


@test
def test_no_format_match_flags():
    TMP.mkdir(exist_ok=True)
    _render(TMP / "a.png", (1500, 2100))
    cfg = _config()
    cfg.fields[0].format = r"ZZZ\d{3}"
    out = _wire(cfg).run([{"path": str(TMP / "a.png"), "name": "a.png"}])[0]["fields"]
    assert out["invoice_number"]["format_matched"] is False
    assert out["invoice_number"]["raw"] == "INV-000123"


if __name__ == "__main__":
    test.main()

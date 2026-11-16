"""Multimodal extraction of World health statistics 2023 into page-linked chunks.

Produces (under --out, default bonus/data):
  chunks_base.json   text + table chunks (kind=text|table), each with page and bbox
  figures.json       one record per figure (caption, page, bbox, crop png, text inside the figure)
  crops/*.png        cropped figure regions (for human verification and vision description)
  extract_report.json  pages with figures/tables, pages not handled and why
Page = physical PDF page (1-based). Nothing here calls an external service.
"""
import argparse
import json
import re
from pathlib import Path

import pymupdf

SOURCE_ID = "who-whs-2023"
FIG_RE = re.compile(r"^Figure\W{0,3}(\d+\.\d+)\s+[A-Z(]")
ANNEX_FIRST = 96  # annex statistical tables start here (verified: find_tables detects tables pp. 96-127)
MAX_TEXT = 1000


def norm(s):
    return re.sub(r"[ \t\u2009\u00a0]+", " ", s).strip()


def split_text(text, size=MAX_TEXT):
    paras = [p.strip() for p in re.split(r"\n\s*\n|(?<=[.:?!])\n(?=[A-Z])", text) if p.strip()]
    out, cur = [], ""
    for p in paras:
        if cur and len(cur) + len(p) + 1 > size:
            out.append(cur)
            cur = p
        else:
            cur = f"{cur}\n{p}".strip()
    if cur:
        out.append(cur)
    final = []
    for c in out:
        while len(c) > size * 1.5:
            cut = c.rfind(". ", 0, size) + 1 or size
            final.append(c[:cut].strip())
            c = c[cut:].strip()
        final.append(c)
    return final


def table_rows(page, tab):
    """Rows as lists of cell strings; text taken per cell rectangle so word spaces are kept."""
    rows = []
    for r in tab.rows:
        cells = [norm(" ".join(page.get_textbox(pymupdf.Rect(c)).split())) if c else "" for c in r.cells]
        if any(cells):
            rows.append(cells)
    return rows


YEAR_RE = re.compile(r"^\d{4}(–\d{4})?$")


def body_start(rows):
    """Index of the first data row: the row after the first row whose non-empty cells (after col 0) are all years."""
    for i, r in enumerate(rows[:10]):
        vals = [c for c in r[1:] if c]
        if vals and all(YEAR_RE.match(c) for c in vals):
            return i + 1
    return 1


def md_row(cells):
    return "| " + " | ".join(cells) + " |"


def find_figures(page):
    blocks = page.get_text("blocks")
    caps, sources = [], []
    for b in blocks:
        t = b[4].strip()
        m = FIG_RE.match(t.replace("\n", " "))
        if m and b[1] < page.rect.height - 60:
            caps.append((b[1], m.group(1), norm(t.replace("\n", " ")), b))
        if t.startswith("Source:") or t.startswith("Sources:"):
            sources.append(b)
    caps.sort(key=lambda x: x[0])
    figs = []
    for i, (y0, num, caption, b) in enumerate(caps):
        nxt = caps[i + 1][0] if i + 1 < len(caps) else page.rect.height - 30
        src = [s for s in sources if s[1] > y0 and s[1] < nxt]
        y1 = (min(src, key=lambda s: s[1])[3] + 4) if src else nxt - 2
        figs.append({"figure": num, "caption": caption, "bbox": [28.0, max(y0 - 4, 0), page.rect.width - 28.0, min(y1, page.rect.height)]})
    return figs


def inside(b, bbox):
    return b[0] >= bbox[0] - 2 and b[2] <= bbox[2] + 2 and b[1] >= bbox[1] - 2 and b[3] <= bbox[3] + 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True, type=Path)
    ap.add_argument("--out", type=Path, default=Path("bonus/data"))
    ap.add_argument("--dpi", type=int, default=130)
    args = ap.parse_args()
    (args.out / "crops").mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(args.pdf)
    chunks, figures, report = [], [], {"pages": len(doc), "table_pages": [], "figure_pages": [], "no_text_pages": [], "notes": []}
    prev_rows = {}
    for pno in range(1, len(doc) + 1):
        page = doc[pno - 1]
        figs = find_figures(page)
        for f in figs:
            crop = args.out / "crops" / f"fig{f['figure']}_p{pno:03d}.png"
            page.get_pixmap(dpi=args.dpi, clip=pymupdf.Rect(*f["bbox"])).save(crop)
            inner = " ".join(norm(b[4].replace("\n", " ")) for b in page.get_text("blocks") if inside(b, f["bbox"]))
            figures.append({"id": f"{SOURCE_ID}-p{pno:03d}-fig{f['figure']}", "source_id": SOURCE_ID, "source": args.pdf.name,
                            "page": pno, "figure": f["figure"], "caption": f["caption"], "bbox": [round(x, 1) for x in f["bbox"]],
                            "crop": crop.name, "text_in_figure": inner})
        if figs:
            report["figure_pages"].append(pno)
        tables = page.find_tables().tables if True else []
        tboxes = []
        n = 0
        for tab in tables:
            rows = table_rows(page, tab)
            if len(rows) < 2:
                continue
            tboxes.append(tab.bbox)
            start = body_start(rows) if pno >= ANNEX_FIRST else 1
            header, body = rows[:start], rows[start:]
            if pno >= ANNEX_FIRST:
                if pno % 2 == 1 and pno - 1 in prev_rows and len(prev_rows[pno - 1][1]) == len(body):
                    names = [r[0] for r in prev_rows[pno - 1][1]]  # right-hand page of a spread: add country names
                    body = [[nm] + r for nm, r in zip(names, body)]
                    header = [["Countries and areas"] + r if i == len(header) - 1 else [""] + r for i, r in enumerate(header)]
                elif pno % 2 == 1:
                    report["notes"].append(f"p{pno}: could not align country names with page {pno - 1}")
                prev_rows[pno] = (header, body)
            per = 12 if pno >= ANNEX_FIRST else 40
            for i in range(0, max(len(body), 1), per):
                grp = body[i:i + per]
                text = chr(10).join(md_row(r) for r in header + grp)
                chunks.append({"id": f"{SOURCE_ID}-p{pno:03d}-table-{n:03d}", "text": text, "source_id": SOURCE_ID, "source": args.pdf.name,
                               "page": pno, "metadata": {"kind": "table", "bbox": [round(x, 1) for x in tab.bbox], "rows": f"{i + 1}-{i + len(grp)}"}})
                n += 1
        if tboxes:
            report["table_pages"].append(pno)
        # text outside tables and outside figure crops
        keep = []
        for b in page.get_text("blocks"):
            if b[6] != 0:
                continue
            if any(inside(b, f["bbox"]) for f in figs):
                continue
            if any(inside(b, tb) or (b[1] >= tb[1] and b[3] <= tb[3] and b[0] >= tb[0] - 2 and b[2] <= tb[2] + 2) for tb in tboxes):
                continue
            t = norm(re.sub(r"(?<=\w)-\n(?=[a-z])", "", b[4]).replace("\n", " "))
            if re.fullmatch(r"\d{0,3}\s*World health statistics 2023.*|\d{1,3}", t):
                continue  # running header / page number
            if t:
                keep.append(t)
        text = "\n\n".join(keep)
        if not text.strip() and not figs and not tboxes:
            report["no_text_pages"].append(pno)
        for i, c in enumerate(split_text(text)):
            if len(c) < 25:
                continue
            chunks.append({"id": f"{SOURCE_ID}-p{pno:03d}-text-{i:03d}", "text": c, "source_id": SOURCE_ID, "source": args.pdf.name,
                           "page": pno, "metadata": {"kind": "text"}})
    ids = [c["id"] for c in chunks]
    assert len(ids) == len(set(ids)), "duplicate ids"
    (args.out / "chunks_base.json").write_text(json.dumps(chunks, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (args.out / "figures.json").write_text(json.dumps(figures, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    report.update({"chunks": len(chunks), "figures": len(figures)})
    (args.out / "extract_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in report.items()}))


if __name__ == "__main__":
    main()

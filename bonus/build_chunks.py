"""Merge text/table chunks and figure chunks into bonus/data/chunks.json (no external calls).

Figure chunk = caption + text layer found inside the figure crop (+ optional vision description from
bonus/data/figure_descriptions.json if it exists). The crop file name is kept in metadata for verification."""
import json
from pathlib import Path

D = Path(__file__).resolve().parent / "data"
base = json.loads((D / "chunks_base.json").read_text(encoding="utf-8"))
figs = json.loads((D / "figures.json").read_text(encoding="utf-8"))
desc_path = D / "figure_descriptions.json"
desc = json.loads(desc_path.read_text(encoding="utf-8")) if desc_path.exists() else {}
out = list(base)
for f in figs:
    parts = [f["caption"], "[Text layer in figure] " + f["text_in_figure"]]
    if f["id"] in desc:
        parts.append("[Vision description] " + desc[f["id"]])
    out.append({"id": f["id"], "text": "\n".join(parts), "source_id": f["source_id"], "source": f["source"], "page": f["page"],
                "metadata": {"kind": "figure", "figure": f["figure"], "bbox": f["bbox"], "crop": f["crop"],
                             "has_vision_description": f["id"] in desc}})
assert len({c["id"] for c in out}) == len(out)
out.sort(key=lambda c: (c["page"], c["id"]))
(D / "chunks.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(len(out), "chunks;", sum(1 for c in out if c["metadata"]["kind"] == "figure"), "figure chunks")

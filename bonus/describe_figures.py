"""Figure branch: describe every figure crop with a vision model (cached, resumable).

Output: bonus/data/figure_descriptions.json  {figure_chunk_id: description}
        bonus/data/figure_descriptions_meta.json  (model, calls, tokens, errors)
Descriptions are model output: they must be checked against the crop before being trusted as evidence.
"""
import argparse
import json
import time

import common

PROMPT = """You are transcribing a figure from the WHO report "World health statistics 2023" so that it can be searched and quoted.
Caption: {caption}

Write a faithful plain-text description of THIS figure only:
1. Type of figure (line chart, bar chart, choropleth map, table-like graphic, timeline, ...), panels, axes with units, legend categories.
2. Every data value that is printed as a label, as "category/series/year: value unit". For maps, give the legend classes (ranges and colours) and name regions/countries only when clearly identifiable for the highest and lowest classes.
3. Main comparisons and trends that are directly visible (highest, lowest, direction of change).
Rules: copy numbers exactly as printed; never estimate a value that is not printed (say "not labelled" instead); do not use outside knowledge; no markdown tables; at most 350 words."""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gemini-3.8-flash")
    ap.add_argument("--only", nargs="*", help="figure numbers, e.g. 2.20 1.6")
    args = ap.parse_args()
    common.load_env()
    figs = json.loads((common.DATA / "figures.json").read_text(encoding="utf-8"))
    out_path = common.DATA / "figure_descriptions.json"
    out = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {}
    meta_path = common.DATA / "figure_descriptions_meta.json"
    old_meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    # which model described which figure (earlier runs recorded a single "model" for all of them)
    models = old_meta.get("models") or {fid: old_meta.get("model", "gemini-2.5-flash") for fid in out}
    started = time.perf_counter()
    errors = []
    for f in figs:
        if args.only and f["figure"] not in args.only:
            continue
        if f["id"] in out:
            continue
        try:
            text = common.generate(args.model, PROMPT.format(caption=f["caption"]),
                                   image_path=common.DATA / "crops" / f["crop"], max_tokens=4096, thinking_budget=0)
        except common.ApiError as e:
            errors.append({"id": f["id"], "error": str(e)[:300]})
            print("ERROR", f["id"], str(e)[:160], flush=True)
            continue
        out[f["id"]] = text
        models[f["id"]] = args.model
        out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("ok", f["id"], len(text), flush=True)
    meta = {"models": models, "described": len(out), "figures": len(figs), "errors_last_run": errors, "last_run_model": args.model,
            "last_run_seconds": round(time.perf_counter() - started, 1),
            "last_run_stats": {k: v for k, v in common.STATS.items() if k != "errors"}}
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()

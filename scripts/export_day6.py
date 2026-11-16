"""Export Day 6 chunks (pgvector table day6_chunks) to the Day 7 chunk contract.

Reads only text/metadata (no vectors, no secrets). Connection string comes from
DATABASE_URL (default: the local-only Day 6 docker-compose database).
"""
import argparse
import json
import os
from pathlib import Path

import psycopg

DEFAULT_URL = "postgresql://day6:day6_local_only@127.0.0.1:55433/day6_lab"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", default="B", choices=["A", "B", "C"])
    ap.add_argument("--output", type=Path, default=Path("data/chunks.json"))
    args = ap.parse_args()
    url = os.environ.get("DATABASE_URL", DEFAULT_URL)
    with psycopg.connect(url) as conn:
        rows = conn.execute(
            "SELECT chunk_id, document_id, source, page, text, metadata FROM day6_chunks "
            "WHERE strategy = %s ORDER BY page, chunk_id", (args.strategy,)).fetchall()
    chunks = [{"id": r[0], "text": r[4], "source_id": r[1], "source": r[2], "page": r[3],
               "metadata": {**r[5], "day6_strategy": args.strategy, "day6_chunk_id": r[0]}} for r in rows]
    ids = [c["id"] for c in chunks]
    assert len(ids) == len(set(ids)), "duplicate chunk ids"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(chunks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"exported {len(chunks)} chunks (strategy {args.strategy}) -> {args.output}")


if __name__ == "__main__":
    main()

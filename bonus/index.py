"""Single merged index: embed every chunk (text + table + figure) and upsert into pgvector.

Same embedding setup as Day 6 (gemini-embedding-001, 768 dims, L2-normalised, RETRIEVAL_DOCUMENT) and the same
PostgreSQL + pgvector instance, in separate tables (day7_chunks, day7_embedding_cache) so Day 6 data is untouched.
Idempotent: unchanged chunks are skipped (content hash), embeddings are cached, obsolete chunks are deleted.
"""
import json
import time

import common

DOC_TASK = "RETRIEVAL_DOCUMENT"


def create_schema(conn):
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    conn.execute(f"""CREATE TABLE IF NOT EXISTS day7_chunks (
        corpus text NOT NULL, chunk_id text NOT NULL, kind text NOT NULL, source text NOT NULL, page int NOT NULL,
        text text NOT NULL, content_hash text NOT NULL, metadata jsonb NOT NULL DEFAULT '{{}}',
        embedding vector({common.EMBED_DIM}) NOT NULL, ingested_at timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY (corpus, chunk_id))""")
    conn.execute(f"""CREATE TABLE IF NOT EXISTS day7_embedding_cache (
        model text NOT NULL, task text NOT NULL, text_hash text NOT NULL, embedding vector({common.EMBED_DIM}) NOT NULL,
        PRIMARY KEY (model, task, text_hash))""")


def cached_embed(conn, text, task):
    h = common.text_hash(text)
    row = conn.execute("SELECT embedding::text FROM day7_embedding_cache WHERE model=%s AND task=%s AND text_hash=%s",
                       (common.EMBED_MODEL, task, h)).fetchone()
    if row:
        return json.loads(row[0]), True
    v = common.embed(text, task)
    conn.execute("INSERT INTO day7_embedding_cache (model, task, text_hash, embedding) VALUES (%s,%s,%s,%s::vector) ON CONFLICT DO NOTHING",
                 (common.EMBED_MODEL, task, h, common.vec_literal(v)))
    conn.commit()
    return v, False


def main():
    common.load_env()
    chunks = json.loads((common.DATA / "chunks.json").read_text(encoding="utf-8"))
    stats = {"chunks": len(chunks), "inserted": 0, "updated": 0, "unchanged": 0, "deleted": 0, "cache_hits": 0, "api_embedded": 0}
    started = time.perf_counter()
    with common.connect() as conn:
        create_schema(conn)
        conn.commit()
        existing = dict(conn.execute("SELECT chunk_id, content_hash FROM day7_chunks WHERE corpus=%s", (common.CORPUS,)).fetchall())
        for i, c in enumerate(chunks):
            h = common.text_hash(c["text"])
            if existing.get(c["id"]) == h:
                stats["unchanged"] += 1
                continue
            v, hit = cached_embed(conn, c["text"], DOC_TASK)
            stats["cache_hits" if hit else "api_embedded"] += 1
            stats["updated" if c["id"] in existing else "inserted"] += 1
            conn.execute("""INSERT INTO day7_chunks (corpus, chunk_id, kind, source, page, text, content_hash, metadata, embedding)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::vector)
                            ON CONFLICT (corpus, chunk_id) DO UPDATE SET kind=EXCLUDED.kind, source=EXCLUDED.source, page=EXCLUDED.page,
                              text=EXCLUDED.text, content_hash=EXCLUDED.content_hash, metadata=EXCLUDED.metadata,
                              embedding=EXCLUDED.embedding, ingested_at=now()""",
                         (common.CORPUS, c["id"], c["metadata"]["kind"], c["source"], c["page"], c["text"], h,
                          json.dumps(c["metadata"], ensure_ascii=False), common.vec_literal(v)))
            conn.commit()
            if (i + 1) % 50 == 0:
                print(f"{i + 1}/{len(chunks)}", flush=True)
        stats["deleted"] = conn.execute("DELETE FROM day7_chunks WHERE corpus=%s AND NOT (chunk_id = ANY(%s))",
                                        (common.CORPUS, [c["id"] for c in chunks])).rowcount
        conn.commit()
        stats["db_rows"] = conn.execute("SELECT count(*) FROM day7_chunks WHERE corpus=%s", (common.CORPUS,)).fetchone()[0]
        stats["by_kind"] = dict(conn.execute("SELECT kind, count(*) FROM day7_chunks WHERE corpus=%s GROUP BY 1", (common.CORPUS,)).fetchall())
    stats.update({"seconds": round(time.perf_counter() - started, 1), "embedding_model": common.EMBED_MODEL, "dimensions": common.EMBED_DIM,
                  "chars_embedded": sum(len(c["text"]) for c in chunks), "api_calls": common.STATS["api_calls"], "retries": common.STATS["retries"]})
    (common.DATA / "index_stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()

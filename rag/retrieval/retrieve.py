"""Metadata filter → BM25 (+ dense if available) → Reciprocal Rank Fusion → top-k.

A cross-encoder reranker is an optional later step, added only if evaluation shows a need.
Paragraph-level chunks are preferred so citations point at a specific 항.
"""


def rrf(rankings: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    score = {}
    for ranking in rankings:
        for r, cid in enumerate(ranking):
            score[cid] = score.get(cid, 0.0)+1.0/(k+r+1)
    return sorted(score.items(), key=lambda x: -x[1])


def search(index, query: str, k: int = 5, docs=None, levels=('paragraph', 'article'), pool: int = 30):
    """→ list of (Chunk, score), best first. docs: restrict to these document names."""
    cand = {i for i, c in enumerate(index.chunks)
            if c.meta.get('level') in levels and (docs is None or c.meta['doc'] in docs)}
    lists = [[index.chunks[i].chunk_id for i, _ in index.bm25(query, cand)[:pool]]]
    dense = index.dense(query, cand)[:pool]
    if dense:
        lists.append([index.chunks[i].chunk_id for i, _ in dense])
    fused = rrf(lists)
    out, seen_parent = [], set()
    for cid, s in fused:
        c = index.by_id[cid]
        parent = c.parent_id or c.chunk_id
        if parent in seen_parent:             # one hit per article
            continue
        seen_parent.add(parent)
        out.append((c, s))
        if len(out) == k:
            break
    return out

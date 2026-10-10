"""Search index over chunks: BM25 always; dense (bge-m3) added when sentence-transformers is
installed. index_version = corpus date + chunk count, recorded on every card."""
import math
from collections import Counter

from rag.indexing.tokenizer import backend, tokenize

K1, B = 1.2, 0.75


class HybridIndex:
    def __init__(self, chunks, version: str, dense_model: str | None = None):
        self.chunks = chunks
        self.version = version
        self.by_id = {c.chunk_id: c for c in chunks}
        self.docs = [Counter(tokenize(c.text)) for c in chunks]
        self.len = [sum(d.values()) for d in self.docs]
        self.avg = sum(self.len)/max(len(self.len), 1)
        df = Counter(t for d in self.docs for t in d)
        n = len(chunks)
        self.idf = {t: math.log(1+(n-f+.5)/(f+.5)) for t, f in df.items()}
        self.tokenizer = backend()
        self.encoder = self.emb = None
        if dense_model:
            try:                                            # optional dependency
                from sentence_transformers import SentenceTransformer
                self.encoder = SentenceTransformer(dense_model)
                self.emb = self.encoder.encode([c.text for c in chunks], normalize_embeddings=True)
            except Exception:
                self.encoder = None

    def bm25(self, query: str, candidates=None):
        q = Counter(tokenize(query))
        scores = []
        for i, d in enumerate(self.docs):
            if candidates is not None and i not in candidates:
                continue
            s = 0.0
            for t in q:
                f = d.get(t, 0)
                if f:
                    s += self.idf[t]*f*(K1+1)/(f+K1*(1-B+B*self.len[i]/self.avg))
            if s > 0:
                scores.append((i, s))
        return sorted(scores, key=lambda x: -x[1])

    def dense(self, query: str, candidates=None):
        if self.encoder is None:
            return []
        qv = self.encoder.encode([query], normalize_embeddings=True)[0]
        sims = self.emb@qv
        idx = [i for i in range(len(self.chunks)) if candidates is None or i in candidates]
        return sorted(((i, float(sims[i])) for i in idx), key=lambda x: -x[1])

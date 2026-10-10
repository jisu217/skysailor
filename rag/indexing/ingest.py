"""Corpus → chunks → HybridIndex.

python -m rag.indexing.ingest [--country kr]     prints chunk and token stats
"""
import argparse
import json
from pathlib import Path

from rag.indexing.chunking import chunk_law, chunk_prose
from rag.indexing.index import HybridIndex

CORPUS = Path(__file__).resolve().parents[1]/'corpus'


def load_chunks(country: str = 'kr', corpus: Path = CORPUS):
    chunks, dates = [], []
    for kind, fn in (('laws', chunk_law), ('precedents', chunk_prose), ('procedures', chunk_prose)):
        for txt in sorted((corpus/country/kind).glob('*.txt')):
            meta = json.loads(txt.with_suffix('.meta.json').read_text(encoding='utf-8'))
            dates.append(meta.get('effective_date', ''))
            chunks += fn(txt.read_text(encoding='utf-8'), meta)
    return chunks, max(dates, default='')


def build(country: str = 'kr', dense_model: str | None = None) -> HybridIndex:
    chunks, latest = load_chunks(country)
    return HybridIndex(chunks, f'{country}-{latest}-{len(chunks)}', dense_model)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--country', default='kr')
    ap.add_argument('--dense', default=None, help='e.g. BAAI/bge-m3 (needs sentence-transformers)')
    a = ap.parse_args()
    ix = build(a.country, a.dense)
    docs = sorted({c.meta['doc'] for c in ix.chunks})
    print(f'index {ix.version}: {len(ix.chunks)} chunks from {len(docs)} documents, tokenizer={ix.tokenizer}, dense={ix.encoder is not None}')
    for d in docs:
        print(f'  {d}: {sum(c.meta["doc"] == d for c in ix.chunks)} chunks')


if __name__ == '__main__':
    main()

"""Evaluate the response card against rag/eval/qrels.jsonl. See rag/docs/DESIGN.md §6.

python -m rag.eval.evaluate [--verbose]

- Action: recommended vs expected → exact / within acceptable / over / under
- Cases: hit@3 (any relevant case among the three shown)
- Articles: recall (any relevant article cited) — only for scenarios that list articles
- Citation: share of shown citations that pass the source check
- Consistency: the same situation run twice gives an identical card

The expected answers are a draft; they measure agreement with the drafted policy, not ground truth.
"""
import argparse
import json
from pathlib import Path

from ops.core.schemas import Threat
from rag.cases.match import load
from rag.generation.escalation import LADDER
from rag.generation.recommend import recommend
from rag.indexing.ingest import build

QRELS = Path(__file__).with_name('qrels.jsonl')


def run(verbose=False):
    ix, cases = build('kr'), load('kr')
    rows = [json.loads(l) for l in QRELS.read_text(encoding='utf-8').splitlines() if l.strip()]
    m = dict(exact=0, within=0, over=0, under=0, case_hit=0, case_n=0, art_hit=0, art_n=0, cites=0, cites_ok=0, consistent=0)
    for q in rows:
        th = Threat(track_id=q['scenario_id'], score=80, level=q['threat_level'], p_hostile=.9, consequence=1, urgency=1, tti_s=120)
        r = recommend(q['situation'], th, ix, cases)
        r2 = recommend(q['situation'], th, ix, cases)
        rec, exp = r.recommended_action, q['expected_action']
        m['exact'] += rec == exp
        m['within'] += rec in q['acceptable']
        if rec not in q['acceptable']:
            m['over' if LADDER.index(rec) > max(LADDER.index(a) for a in q['acceptable']) else 'under'] += 1
        shown = [c.case_id for c in r.similar_cases]
        if q['relevant_cases']:
            m['case_n'] += 1
            m['case_hit'] += any(c in shown for c in q['relevant_cases'])
        cited = [f'{c.citation.doc}|{c.citation.article}' for c in r.constraints if c.citation]
        if q['relevant_articles']:
            m['art_n'] += 1
            m['art_hit'] += any(any(x.startswith(a) for x in cited) for a in q['relevant_articles'])
        m['cites'] += len(cited)
        m['cites_ok'] += sum(c.citation.verified for c in r.constraints if c.citation)
        m['consistent'] += r.model_dump() == r2.model_dump()
        if verbose:
            flag = '✓' if rec == exp else ('~' if rec in q['acceptable'] else '✗')
            print(f"{flag} {q['scenario_id']} {q['situation']['target_class']}/{q['situation']['zone_type']}/{q['situation']['population']} "
                  f"{q['threat_level']}: 권고 {rec} (정답 {exp}) | 사례 {shown[:3]}")
    n = len(rows)
    out = dict(scenarios=n, index=ix.version, cases=len(cases),
               action_exact=m['exact']/n, action_within_acceptable=m['within']/n, over=m['over']/n, under=m['under']/n,
               case_hit_at_3=m['case_hit']/max(m['case_n'], 1), article_recall=m['art_hit']/max(m['art_n'], 1),
               citation_verified=m['cites_ok']/max(m['cites'], 1), consistency=m['consistent']/n)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--verbose', action='store_true')
    res = run(ap.parse_args().verbose)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

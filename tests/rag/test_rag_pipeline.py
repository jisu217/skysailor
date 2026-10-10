import pytest

from ops.core.schemas import Citation, Threat
from rag.cases.match import load
from rag.generation.recommend import recommend
from rag.generation.verify import verify
from rag.indexing.chunking import chunk_law
from rag.indexing.ingest import build
from rag.retrieval.query import ACTION_DOCS, queries
from rag.retrieval.retrieve import rrf, search

LAW = """제1조(목적) 이 법은 시험용이다.
제2조(정의)
① 첫째 항이다.
  1. 첫째 호
② 둘째 항이다.
제3조 삭제 <2020.1.1>
제4조(끝) 마지막 조문이다.
"""


@pytest.fixture(scope='module')
def ix():
    return build('kr')


@pytest.fixture(scope='module')
def cases():
    return load('kr')


def _threat(level, tti=120):
    return Threat(track_id='T', score=80, level=level, p_hostile=.9, consequence=1, urgency=1, tti_s=tti)


def test_chunk_law_splits_articles_and_paragraphs():
    ch = chunk_law(LAW, dict(doc='시험법', law_id='X'))
    ids = [c.chunk_id for c in ch]
    assert ids == ['X:제1조', 'X:제2조', 'X:제2조:1', 'X:제2조:2', 'X:제4조']
    assert not any('삭제' in c.text for c in ch)
    p1 = next(c for c in ch if c.chunk_id == 'X:제2조:1')
    assert '첫째 호' in p1.text and p1.parent_id == 'X:제2조' and p1.meta['article'] == '제2조 제1항'


def test_rrf_fusion_order():
    fused = [cid for cid, _ in rrf([['a', 'b', 'c'], ['b', 'a', 'd']])]
    assert fused[:2] == ['a', 'b'] or fused[:2] == ['b', 'a']
    assert fused.index('c') > 1 and fused.index('d') > 1


def test_jamming_query_finds_radio_act_exception(ix):
    q = queries(dict(zone_type='capital'), ['rf_jam'])['rf_jam']
    top = search(ix, q, k=3, docs=ACTION_DOCS['rf_jam'])
    assert top[0][0].meta['doc'] == '전파법' and top[0][0].meta['article'] == '제29조 제3항'


def test_verify_rejects_fabricated_quote(ix):
    chunk = ix.by_id[search(ix, '전파차단장치', k=1, docs=('전파법',))[0][0].chunk_id]
    real = Citation(chunk_id=chunk.chunk_id, doc='전파법', article='', quote=chunk.text.split('\n')[1][:40])
    fake = Citation(chunk_id=chunk.chunk_id, doc='전파법', article='', quote='누구든지 드론을 자유롭게 격추할 수 있다')
    assert verify(real, chunk) and not verify(fake, chunk)


def test_recommendation_stays_inside_allowed_range(ix, cases):
    sit = dict(target_class='drone', zone_type='capital', population='high', rid='none')
    r = recommend(sit, _threat('HIGH'), ix, cases)
    assert r.recommended_action in r.allowed_range == ['observe', 'report', 'alert']
    assert r.action_status['rf_jam'] == 'out' and r.action_status['kinetic'] == 'out'


def test_crowd_excludes_kinetic_and_jamming_needs_authority(ix, cases):
    sit = dict(target_class='drone', zone_type='capital', population='high', rid='none')
    r = recommend(sit, _threat('CRITICAL'), ix, cases)
    assert r.action_status['kinetic'] == 'excluded' and r.action_status['rf_jam'] == 'conditional'
    jam = [c for c in r.constraints if 'rf_jam' in c.applies_to and c.citation]
    assert jam and all(c.citation.verified for c in jam) and jam[0].citation.doc == '전파법'
    assert r.recommended_action == 'alert'                   # conditional actions are never auto-recommended


def test_no_evidence_falls_back_to_observe(ix, cases):
    sit = dict(target_class='bird', zone_type='capital', population='low', rid='none')
    r = recommend(sit, _threat('HIGH'), ix, cases)
    assert r.recommended_action == 'observe' and not r.evidence_sufficient


def test_permitted_drone_limited_to_report(ix, cases):
    sit = dict(target_class='drone', zone_type='capital', population='medium', rid='present', permitted=True)
    r = recommend(sit, _threat('CRITICAL'), ix, cases)
    assert r.recommended_action == 'report' and r.action_status['alert'] == 'excluded'


def test_same_situation_same_card(ix, cases):
    sit = dict(target_class='balloon', zone_type='airport', population='medium', rid='none')
    a, b = recommend(sit, _threat('HIGH'), ix, cases), recommend(sit, _threat('HIGH'), ix, cases)
    assert a.model_dump() == b.model_dump()


def test_evaluation_never_over_recommends():
    from rag.eval.evaluate import run
    res = run()
    assert res['scenarios'] == 20 and res['over'] == 0 and res['consistency'] == 1.0
    assert res['citation_verified'] == 1.0

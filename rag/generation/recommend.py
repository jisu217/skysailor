"""Build the three-part card (ops.core.schemas.Recommendation). See rag/docs/DESIGN.md §4–5.

1. allowed range      escalation.ALLOWED[threat.level] — fixed, reviewable table
2. operational limits  exclude actions the situation rules out (crowd below → no kinetic, balloon →
                       no jamming, permitted Remote ID → report at most)
3. legal basis         per remaining action that needs one, search the statutes; jamming and kinetic
                       become 'conditional' (authority required) with the found articles cited, or
                       'excluded' when nothing is found. Every quote is checked against its chunk.
4. similar cases       rag.cases.match → the highest level past responses reached
5. recommendation      highest *unconditional* allowed action not above the case maximum;
                       no similar case → 'observe' with evidence_sufficient=False

Template mode only: sentences are filled from the evidence, nothing is generated.
"""
from ops.core.schemas import Citation, Constraint, Recommendation
from rag.cases.match import similar
from rag.generation.escalation import ALLOWED, LADDER
from rag.generation.verify import verify
from rag.retrieval.query import ACTION_DOCS, queries
from rag.retrieval.retrieve import search

KO = dict(observe='관측 지속', report='관계기관 통보', alert='경보 발령', rf_jam='전파 차단', kinetic='물리적 무력화')
NEEDS_AUTHORITY = ('rf_jam', 'kinetic')
CROWD = 'high'
DEADLINE_MARGIN = dict(drone=60.0, balloon=120.0)


def _quote(chunk, n: int = 160) -> str:
    body = chunk.text.split('\n', 1)[-1].strip()
    return body if len(body) <= n else body[:n].rsplit(' ', 1)[0]+' …'


def _cite(chunk) -> Citation:
    c = Citation(chunk_id=chunk.chunk_id, doc=chunk.meta['doc'], article=chunk.meta['article'],
                 quote=_quote(chunk).removesuffix(' …'))
    c.verified = verify(c, chunk)
    if c.quote != _quote(chunk):
        c.quote += ' …'
    return c


def recommend(situation: dict, threat, index, cases, k_legal: int = 2) -> Recommendation:
    allowed = ALLOWED[threat.level]
    status = {a: 'allowed' if a in allowed else 'out' for a in LADDER}
    cons = []

    if situation.get('permitted'):
        for a in ('alert', 'rf_jam', 'kinetic'):
            if status[a] == 'allowed':
                status[a] = 'excluded'
        cons.append(Constraint(kind='operational', text='Remote ID로 확인된 허가 비행체 → 신원 확인·통보로 한정', applies_to=['alert', 'rf_jam', 'kinetic']))
    if situation['population'] == CROWD and status['kinetic'] == 'allowed':
        status['kinetic'] = 'excluded'
        cons.append(Constraint(kind='operational', text='인구 밀집 지역 상공 → 격추 시 낙하물로 부수 피해', applies_to=['kinetic']))
    if situation['target_class'] == 'balloon' and status['rf_jam'] == 'allowed':
        status['rf_jam'] = 'excluded'
        cons.append(Constraint(kind='operational', text='풍선은 무선 조종이 아니어서 전파 차단 효과 없음', applies_to=['rf_jam']))

    need = [a for a in LADDER if status[a] == 'allowed' and a != 'observe']
    for a, q in queries(situation, need).items():
        hits = [_cite(c) for c, _ in search(index, q, k=k_legal, docs=ACTION_DOCS.get(a))]
        hits = [h for h in hits if h.verified]
        if a in NEEDS_AUTHORITY:
            if hits:
                status[a] = 'conditional'
                for h in hits:
                    cons.append(Constraint(kind='legal', text=f'{KO[a]}: 아래 조문의 활동·권한 범위에서만 가능 (근거 후보 · 법률 검토 필요)',
                                           applies_to=[a], citation=h))
            else:
                status[a] = 'excluded'
                cons.append(Constraint(kind='legal', text=f'{KO[a]}: 검색된 법적 근거 없음', applies_to=[a]))
        else:
            for h in hits[:1]:
                cons.append(Constraint(kind='legal', text=f'{KO[a]} 관련 조문', applies_to=[a], citation=h))

    refs = similar(situation, cases)
    case_max = max((LADDER.index(m) for m in (_max_action(cases, r.case_id) for r in refs)), default=-1)
    usable = [a for a in LADDER if status[a] == 'allowed']
    rec = 'observe'
    for a in usable:
        if LADDER.index(a) <= case_max:
            rec = a
    enough = bool(refs)
    excluded = [KO[a] for a in LADDER if status[a] == 'excluded']
    conditional = [KO[a] for a in LADDER if status[a] == 'conditional']
    why = f'위협 {threat.level} → 허용 범위 {KO[allowed[0]]}~{KO[allowed[-1]]}'
    if excluded:
        why += f' → 제약으로 {"·".join(excluded)} 제외'
    if conditional:
        why += f' → {"·".join(conditional)}: 권한 기관 조건부'
    why += (f' → 유사 사례 {len(refs)}건의 최고 대응 \'{KO[LADDER[case_max]]}\' 이내에서 {KO[rec]}' if enough
            else ' → 유사 사례 없음: 관측 지속')
    margin = DEADLINE_MARGIN.get(situation['target_class'], 60.0)
    deadline = None if threat.tti_s is None else max(0.0, threat.tti_s-margin)
    return Recommendation(track_id=threat.track_id, mode='template', country='kr', index_version=index.version,
                          similar_cases=refs, constraints=cons, recommended_action=rec, allowed_range=allowed,
                          action_status=status, justification=why, evidence_sufficient=enough, deadline_s=deadline)


def _max_action(cases, case_id):
    return next(c.max_action for c in cases if c.case_id == case_id)

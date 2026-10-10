"""Find similar past cases: weighted field match on the situation, newer cases first on ties.

Case counts are small (tens), so a transparent field match beats vector search here, and
`matched_on` tells the operator why a case was judged similar. A case must share the target
class to count as similar.

Which folders a mode reads: 'kr' → kr + us + intl (any precedent helps a Korean decision),
'us' → us + intl.
"""
import json
from pathlib import Path

from ops.core.schemas import CaseRef
from rag.cases.schema import Case

CORPUS = Path(__file__).resolve().parents[1]/'corpus'
WEIGHTS = dict(target_class=3, zone_type=2, population=1, rid=1)
LABEL = dict(target_class='표적 유형', zone_type='시설 유형', population='인구 밀집도', rid='Remote ID')
MODES = dict(kr=('kr', 'us', 'intl'), us=('us', 'intl'))


def load(country: str = 'kr', corpus: Path = CORPUS) -> list[Case]:
    cases = []
    for folder in MODES.get(country, (country, 'intl')):
        for p in sorted((corpus/folder/'cases').glob('*.json')):
            cases.append(Case.model_validate_json(p.read_text(encoding='utf-8')))
    return cases


def similar(situation: dict, cases, k: int = 3) -> list[CaseRef]:
    """situation: {target_class, zone_type, population, rid} → top-k CaseRef by similarity."""
    total = sum(WEIGHTS.values())
    scored = []
    for c in cases:
        if c.target_class != situation.get('target_class'):
            continue
        matched = [f for f in WEIGHTS if getattr(c, f) == situation.get(f)]
        scored.append((sum(WEIGHTS[f] for f in matched)/total, c.date, c, matched))
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [CaseRef(case_id=c.case_id, title=c.title, date=c.date, actions_taken=c.actions_taken, outcome=c.outcome,
                    constraints=c.constraints, similarity=round(s, 3), matched_on=[LABEL[f] for f in m],
                    source=c.sources[0])
            for s, _, c, m in scored[:k]]


def dump(cases) -> str:
    return json.dumps([c.model_dump() for c in cases], ensure_ascii=False, indent=2)

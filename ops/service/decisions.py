"""⑧ Append-only decision log (JSONL). See ops/docs/DESIGN.md §5.7.

Each line holds the operator's decision plus what they saw at that moment — the threat and
the recommendation card (with its RAG index version) — so any decision can be reviewed later.
Rules:
- approving an action other than the recommended one needs an override reason
- the log is only appended to; nothing is edited or deleted
- latency = decision time − first alert time for that track
"""
import json
import time
import uuid
from pathlib import Path

from ops.core.schemas import Decision

DEFAULT_PATH = Path('outputs/ops/decisions.jsonl')
DECISION_KO = dict(approve='승인', hold='보류', observe_more='추가 관측', dismiss='해제')


class OverrideReasonRequired(ValueError):
    pass


class DecisionLog:
    def __init__(self, path: Path | str = DEFAULT_PATH):
        self.path = Path(path)

    def record(self, decision: Decision, threat=None, recommendation=None, alert_t: float | None = None) -> str:
        """Validate and append. Returns snapshot_ref (also stored on the line)."""
        rec = getattr(recommendation, 'recommended_action', None)
        if decision.decision == 'approve' and rec and decision.action and decision.action != rec \
                and not (decision.override_reason or '').strip():
            raise OverrideReasonRequired(f'권고({rec})와 다른 대응({decision.action})을 승인하려면 사유가 필요합니다')
        ref = uuid.uuid4().hex[:12]
        line = dict(
            ref=ref, logged_at=time.strftime('%Y-%m-%dT%H:%M:%S%z'),
            decision=decision.model_copy(update=dict(snapshot_ref=ref)).model_dump(),
            recommended_action=rec, override=bool(rec and decision.action and decision.action != rec),
            latency_s=None if alert_t is None else round(decision.t-alert_t, 1),
            threat=threat.model_dump() if threat is not None else None,
            recommendation=recommendation.model_dump() if recommendation is not None else None)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open('a', encoding='utf-8') as f:
            f.write(json.dumps(line, ensure_ascii=False)+'\n')
        return ref

    def read(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(l) for l in self.path.read_text(encoding='utf-8').splitlines() if l.strip()]

    def summary(self) -> dict:
        rows = self.read()
        lat = [r['latency_s'] for r in rows if r.get('latency_s') is not None]
        by = {}
        for r in rows:
            k = DECISION_KO.get(r['decision']['decision'], r['decision']['decision'])
            by[k] = by.get(k, 0)+1
        return dict(count=len(rows), by_decision=by,
                    override_rate=(sum(r['override'] for r in rows)/len(rows)) if rows else 0.0,
                    mean_latency_s=round(sum(lat)/len(lat), 1) if lat else None)

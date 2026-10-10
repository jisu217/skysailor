"""/api/ops/* REST + WebSocket for the decision-support screen (prototype: prototypes/c-uas-ops.html).

Implemented: health, decision log. Scenario streaming (WS) comes with the ops server.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ops.core.schemas import Decision, Recommendation, Threat
from ops.service.decisions import DecisionLog, OverrideReasonRequired

router = APIRouter(prefix='/api/ops', tags=['ops'])
log = DecisionLog()
# Set by the server: track_id → (Threat, Recommendation, first alert time) the operator was shown.
snapshot_provider = None


class DecisionIn(BaseModel):
    decision: Decision
    threat: Threat | None = None
    recommendation: Recommendation | None = None
    alert_t: float | None = None


@router.get('/health')
def health():
    return dict(status='ok')


@router.post('/decision', status_code=201)
def post_decision(body: DecisionIn):
    threat, rec, alert_t = body.threat, body.recommendation, body.alert_t
    if snapshot_provider is not None and threat is None:
        threat, rec, alert_t = snapshot_provider(body.decision.track_id)
    try:
        ref = log.record(body.decision, threat, rec, alert_t)
    except OverrideReasonRequired as e:
        raise HTTPException(422, str(e))
    return dict(snapshot_ref=ref)


@router.get('/decisions')
def get_decisions():
    return dict(summary=log.summary(), items=log.read())

# TODO (ops server): POST /scenario/start, GET /state, WS /ws, GET /recommendation/{track_id}

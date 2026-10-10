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
    # Client snapshot fields are accepted for compatibility, never trusted for auditing.
    if snapshot_provider is None:
        raise HTTPException(503, 'Server snapshot provider is unavailable')
    track_id = body.decision.track_id
    threat, rec, alert_t = snapshot_provider(track_id)
    if threat is None:
        raise HTTPException(404, 'No server snapshot exists for this track')
    if threat.track_id != track_id or (rec is not None and rec.track_id != track_id):
        raise HTTPException(409, 'Server snapshot does not match the decision track')
    try:
        ref = log.record(body.decision, threat, rec, alert_t)
    except OverrideReasonRequired as e:
        raise HTTPException(422, str(e))
    return dict(snapshot_ref=ref)


@router.get('/decisions')
def get_decisions():
    return dict(summary=log.summary(), items=log.read())

# TODO (ops server): POST /scenario/start, GET /state, WS /ws, GET /recommendation/{track_id}

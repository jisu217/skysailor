import pytest

from ops.core.schemas import Decision, Recommendation, RemoteID, Threat
from ops.service.decisions import DecisionLog, OverrideReasonRequired

TH = Threat(track_id='T-1', score=82, level='CRITICAL', p_hostile=.9, consequence=1, urgency=.9, tti_s=40)
REC = Recommendation(track_id='T-1', index_version='kr-test', recommended_action='alert',
                     allowed_range=['observe', 'report', 'alert'], justification='test')


def _d(decision='approve', action='alert', reason=None, t=100.0):
    return Decision(track_id='T-1', t=t, operator='op1', decision=decision, action=action, override_reason=reason)


def test_record_keeps_snapshot_and_latency(tmp_path):
    log = DecisionLog(tmp_path/'d.jsonl')
    ref = log.record(_d(), TH, REC, alert_t=82.0)
    (row,) = log.read()
    assert row['ref'] == ref == row['decision']['snapshot_ref']
    assert row['threat']['level'] == 'CRITICAL' and row['recommendation']['index_version'] == 'kr-test'
    assert row['latency_s'] == 18.0 and row['override'] is False


def test_override_needs_reason(tmp_path):
    log = DecisionLog(tmp_path/'d.jsonl')
    with pytest.raises(OverrideReasonRequired):
        log.record(_d(action='rf_jam'), TH, REC)
    assert log.read() == []
    log.record(_d(action='rf_jam', reason='경호처 요청으로 전파 차단'), TH, REC)
    assert log.read()[0]['override'] is True


def test_log_is_append_only_and_summarised(tmp_path):
    log = DecisionLog(tmp_path/'d.jsonl')
    log.record(_d(), TH, REC, alert_t=90)
    log.record(_d(decision='hold', action=None, t=120), TH, REC, alert_t=90)
    log.record(_d(action='report', reason='관측 결과 위협 낮음', t=130), TH, REC, alert_t=90)
    s = log.summary()
    assert s['count'] == 3 and s['by_decision'] == {'승인': 2, '보류': 1}
    assert abs(s['override_rate']-1/3) < 1e-9 and s['mean_latency_s'] == round((10+30+40)/3, 1)


def test_api_rejects_override_without_reason(tmp_path, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import ops.service.api as api
    monkeypatch.setattr(api, 'log', DecisionLog(tmp_path/'d.jsonl'))
    app = FastAPI(); app.include_router(api.router)
    c = TestClient(app)
    body = dict(decision=_d(action='rf_jam').model_dump(), threat=TH.model_dump(), recommendation=REC.model_dump(), alert_t=90)
    assert c.post('/api/ops/decision', json=body).status_code == 422
    body['decision']['override_reason'] = '권한 기관 승인 완료'
    assert c.post('/api/ops/decision', json=body).status_code == 201
    assert c.get('/api/ops/decisions').json()['summary']['count'] == 1


def test_server_live_ingest_and_decision_snapshot(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    import ops.service.api as api
    from ops.core.geo import ENU
    from ops.service.server import create_app
    monkeypatch.setattr(api, 'log', DecisionLog(tmp_path/'d.jsonl'))
    app = create_app(speed=1.0)
    runner = app.state.runner
    with TestClient(app) as c:
        assert c.get('/api/ops/meta').json()['nodes'][0]['id'] == 'dome-1'
        assert c.post('/api/ops/control', json=dict(action='pause')).json()['paused'] is True
        runner.mode = 'live'
        runner.new_session()
        lat, lon, alt = ENU(37.55, 126.99, 0).to_geo([100, 50, 80])
        for k in range(4):                                   # step synchronously instead of waiting for the loop
            frame = runner.session.step_live(k*0.5, [], [], [('dome-1', RemoteID(uas_id='TEST-1', lat=lat, lon=lon, alt=alt))])
        assert [(t['rid'], t['status']) for t in frame['tracks']] == [('TEST-1', 'confirmed')]
        with c.websocket_connect('/api/ops/ws') as ws:
            assert ws.receive_json()['type'] == 'meta'
        r = c.post('/api/ops/decision', json=dict(decision=_d(decision='hold', action=None).model_dump()))
        assert r.status_code == 201

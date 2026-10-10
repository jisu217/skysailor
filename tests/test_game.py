from fastapi.testclient import TestClient
from dashboard import app
import numpy as np


def test_manual_game_paused_reset_bounds_and_deterministic_replay():
    with TestClient(app).websocket_connect('/api/game') as ws:
        ws.send_json({'kind':'reset','preset':'calm'});first=ws.receive_json()
        assert first['frame']['t']==0 and len(first['geometry'])>0
        ws.send_json({'kind':'step','x':2});assert 'error' in ws.receive_json()
        ws.send_json({'kind':'step','x':.5,'y':-.2,'move_seconds':0});r=ws.receive_json()
        assert r['frame']['t']==.02
        assert r['frame']['target_xy']==[.06,-.024]
        assert np.max(np.abs(r['frame']['winch_speed']))<=.04+1e-10
        ws.send_json({'kind':'reset','preset':'calm'});assert ws.receive_json()['frame']==first['frame']
        ws.send_json({'kind':'step','x':.5,'y':-.2,'move_seconds':0});assert ws.receive_json()['frame']==r['frame']


def test_manual_game_triangle_projection_and_independent_sessions():
    client=TestClient(app)
    with client.websocket_connect('/api/game') as a,client.websocket_connect('/api/game') as b:
        for ws,preset in [(a,'gust'),(b,'measured')]:
            ws.send_json({'kind':'reset','preset':preset});ws.receive_json()
        a.send_json({'kind':'step','x':-1,'y':1});ra=a.receive_json()
        b.send_json({'kind':'step','x':0,'y':0});rb=b.receive_json()
        assert ra['frame']['t']==rb['frame']['t']==.02
        assert ra['frame']['wind']!=rb['frame']['wind']
        assert ra['frame']['target_xy'][0]>=-.06000001
        assert rb['frame']['target_xy']==[0,0]


def test_target_transition_time_and_three_dimensional_lengths():
    with TestClient(app).websocket_connect('/api/game') as ws:
        ws.send_json({'kind':'reset'});initial=ws.receive_json()
        for i in range(5):
            ws.send_json({'kind':'step','x':1,'move_seconds':.1});r=ws.receive_json()
            fraction=(i+1)/5
            assert np.isclose(r['frame']['target_xy'][0],.12*fraction*fraction*(3-2*fraction))
            assert np.max(np.abs(r['frame']['winch_speed']))<=.04+1e-10
        assert np.isclose(r['goal_lengths'][0],initial['frame']['hang'])
        assert np.isclose(r['move_remaining'],0)
        ws.send_json({'kind':'step','x':0,'move_seconds':.1});r=ws.receive_json()
        assert np.isclose(r['frame']['target_xy'][0],.12*(1-.2**2*(3-2*.2)))


def test_game_minimum_line_length_and_mass():
    from dome import DomeSim
    sim=DomeSim(line_length=.12,payload_mass=.012)
    assert sim.hang==0
    assert np.isclose(sim.model.body_mass[sim.payload],.012)
    assert np.allclose(sim.lengths_for_target([0,0]),.12)
    assert np.isclose(sim.lengths_for_target([.12,0])[0],0)
    with TestClient(app).websocket_connect('/api/game') as ws:
        ws.send_json({'kind':'reset','line_length_mm':120,'payload_mass_g':12})
        r=ws.receive_json()
        assert r['frame']['hang']==0
        assert np.allclose(r['frame']['line_actual'],.12)
        ws.send_json({'kind':'step','x':.5})
        assert np.isfinite(ws.receive_json()['frame']['height'])
        ws.send_json({'kind':'reset','line_length_mm':119})
        assert 'error' in ws.receive_json()


def test_persistent_flight_logs(tmp_path,monkeypatch):
    import dashboard,json
    monkeypatch.setattr(dashboard,'FLIGHT_LOG_DIR',tmp_path)
    client=TestClient(app)
    with client.websocket_connect('/api/game') as ws:
        ws.send_json({'kind':'reset','payload_mass_g':8})
        first=ws.receive_json()['log_id']
        ws.send_json({'kind':'step','x':.2})
        assert ws.receive_json()['log_id']==first
        ws.send_json({'kind':'reset'})
        assert ws.receive_json()['log_id']!=first
    rows=[json.loads(line) for line in client.get('/api/game/logs/'+first).text.splitlines()]
    assert rows[0]['settings']['payload_mass_g']==8
    assert rows[1]['data']['frame']['t']==0
    assert rows[2]['data']['frame']['t']==.02
    assert rows[2]['input']['x']==.2
    assert len(client.get('/api/game/logs').json())==2
    assert client.get('/api/game/logs/invalid').status_code==404


def test_rewind_restores_and_resumes_identical_physics(tmp_path,monkeypatch):
    import dashboard
    monkeypatch.setattr(dashboard,'FLIGHT_LOG_DIR',tmp_path)
    with TestClient(app).websocket_connect('/api/game') as ws:
        ws.send_json({'kind':'reset','preset':'gust'});initial=ws.receive_json()
        frames=[]
        for _ in range(10):
            ws.send_json({'kind':'step','x':.2,'move_seconds':.5});frames.append(ws.receive_json())
        ws.send_json({'kind':'rewind'});r=ws.receive_json()
        assert r['frame']==frames[4]['frame']
        for expected in frames[5:]:
            ws.send_json({'kind':'step','x':.2,'move_seconds':.5});r=ws.receive_json()
            assert r['frame']==expected['frame']
        for _ in range(3):
            ws.send_json({'kind':'rewind'});r=ws.receive_json()
        assert r['frame']==initial['frame']
        assert r['rewind_available']==0


def test_velocity_input_and_variable_interval(tmp_path,monkeypatch):
    import dashboard
    monkeypatch.setattr(dashboard,'FLIGHT_LOG_DIR',tmp_path)
    with TestClient(app).websocket_connect('/api/game') as ws:
        ws.send_json({'kind':'reset','mechanism':'B4'});ws.receive_json()
        ws.send_json({'kind':'step','input_mode':'velocity','x':.5,'velocity_mm_s':40,'interval_s':.15})
        r=ws.receive_json()['frame']
        assert r['t']==.15
        assert np.isclose(r['payload_local'][0],.003,atol=1e-9)
        ws.send_json({'kind':'step','input_mode':'velocity','interval_s':.05})
        r=ws.receive_json()['frame']
        assert r['t']==.2
        assert np.isclose(r['payload_local'][0],.003,atol=1e-9)
        ws.send_json({'kind':'rewind','interval_s':.15})
        assert ws.receive_json()['frame']['t']==.05


def test_direct_game_actuator_speed_and_rewind(tmp_path,monkeypatch):
    import dashboard
    monkeypatch.setattr(dashboard,'FLIGHT_LOG_DIR',tmp_path)
    with TestClient(app).websocket_connect('/api/game') as ws:
        ws.send_json({'kind':'reset','mechanism':'P','payload_mass_g':18,'connector_drop_mm':250,'actuator_speed_mm_s':350})
        initial=ws.receive_json()['frame']
        assert initial['mechanism']=='P' and initial['hang']==.25
        step={'kind':'step','input_mode':'velocity','x':.8,'y':.4,'z':-.5,'velocity_mm_s':500,'interval_s':.1}
        ws.send_json(step);result=ws.receive_json()
        f=result['frame']
        assert np.isclose(f['t'],.1)
        assert np.max(np.abs(np.array(f['line_target'])-initial['line_target']))<=.035+1e-9
        assert not np.allclose(f['line_target'],initial['line_target'])
        assert f['line_target']==result['goal_lengths']
        ws.send_json({'kind':'rewind','interval_s':.1});rewound=ws.receive_json()['frame']
        assert rewound['t']==0 and rewound['line_target']==initial['line_target']
        ws.send_json(step);repeated=ws.receive_json()['frame']
        assert np.allclose(repeated['position'],f['position'])
        assert np.allclose(repeated['line_target'],f['line_target'])

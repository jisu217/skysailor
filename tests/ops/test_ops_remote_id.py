"""Vectors produced with the reference encoder opendroneid-core-c (libopendroneid, Apache-2.0)."""
import pytest

from ops.sources.remote_id import (Assembler, RawRemoteID, decode, encode_basic, encode_location, encode_pack,
                                   strip_transport)

V = dict(
    basic='02123135393641313233343536373839303100000000000000',
    location='12222416fd19dd61161953b14bad08bc0870084a5339300200',
    location_fast='12232416fd19dd61161953b14bad08bc0870084a5339300200',
    system='4205e1ac6116e122b14b0100000000000012f9072065b70e00',
    selfid='320042726964676520696e7370656374696f6e000000000000',
    operator='52004b4f5238376173747264676531326b3800000000000000',
    pack='f2190202123135393641313233343536373839303100000000000000'
         '12222416fd19dd61161953b14bad08bc0870084a5339300200',
)


def _one(name):
    (m,) = decode(bytes.fromhex(V[name]))
    return m


def test_basic_id():
    m = _one('basic')
    assert (m['type'], m['version'], m['id_type'], m['ua_type'], m['uas_id']) == (0, 2, 'serial', 'multirotor', '1596A12345678901')


def test_location():
    m = _one('location')
    assert m['status'] == 'airborne' and m['height_type'] == 'takeoff'
    assert m['direction'] == 216.0 and m['speed'] == 5.5 and m['vspeed'] == -1.5     # encoder rounds 215.5→216, 5.4→5.5
    assert m['lat'] == pytest.approx(37.5512345, abs=1e-7) and m['lon'] == pytest.approx(126.9912345, abs=1e-7)
    assert (m['alt_baro'], m['alt_geo'], m['height']) == (110.5, 118.0, 80.0)
    assert m['timestamp'] == 1234.5
    assert (m['h_accuracy'], m['v_accuracy'], m['speed_accuracy'], m['baro_accuracy'], m['ts_accuracy']) == (10, 4, 3, 5, 2)


def test_location_speed_multiplier():
    assert _one('location_fast')['speed'] == 80.25


def test_system_selfid_operator():
    s = _one('system')
    assert s['operator_lat'] == pytest.approx(37.5500001, abs=1e-7) and s['operator_alt'] == 20.5
    assert s['timestamp'] == 246900000 and s['area_count'] == 1
    assert _one('selfid')['description'] == 'Bridge inspection'
    assert _one('operator')['operator_id'] == 'KOR87astrdge12k8'


def test_message_pack_and_transport_prefix():
    msgs = decode(bytes.fromhex(V['pack']))
    assert [m['type'] for m in msgs] == [0, 1] and msgs[0]['uas_id'] == '1596A12345678901'
    bt_service_data = bytes([0x0D, 7])+bytes.fromhex(V['location'])
    assert strip_transport(bt_service_data) == bytes.fromhex(V['location'])
    wifi_ie = bytes.fromhex('fa0bbc0d')+bytes([3])+bytes.fromhex(V['pack'])
    assert [m['type'] for m in decode(wifi_ie)] == [0, 1]


def test_encoder_matches_reference():
    assert encode_basic('1596A12345678901').hex() == V['basic']
    loc = encode_location(37.5512345, 126.9912345, 118.0, speed=5.4, direction=215.5, vspeed=-1.5, alt_baro=110.5,
                          height=80.0, timestamp=1234.5, h_acc=10, v_acc=4, speed_acc=3, baro_acc=5, ts_acc=2)
    assert loc.hex() == V['location']
    assert encode_pack([bytes.fromhex(V['basic']), bytes.fromhex(V['location'])]).hex() == V['pack']


def test_assembler_joins_messages_per_sender():
    asm = Assembler()
    raw = lambda hexs: RawRemoteID(node_id='dome-1', received_at=1.0, mac='aa:bb', rssi=-60, payload_hex=hexs)
    assert asm.add(raw(V['location'])) is None                       # no Basic ID yet
    node, rid = asm.add(raw(V['basic']))
    assert node == 'dome-1' and rid.uas_id == '1596A12345678901' and rid.alt == 118.0 and rid.speed == 5.5
    _, rid = asm.add(raw(V['system']))
    assert rid.operator_lat == pytest.approx(37.5500001, abs=1e-7)


def test_server_decodes_raw_frames_into_tracks():
    from fastapi.testclient import TestClient
    from ops.service.server import create_app
    app = create_app(speed=1.0)
    runner = app.state.runner
    with TestClient(app) as c:
        c.post('/api/ops/control', json=dict(action='pause'))
        runner.mode = 'live'
        runner.new_session()
        pack = encode_pack([encode_basic('KR-TEST-1'), encode_location(37.5502, 126.9905, 90.0, speed=4.0, direction=45)])
        frame = dict(node_id='dome-1', received_at=0.0, mac='aa:bb:cc', rssi=-65, transport='bt5', payload_hex=(bytes([0x0D, 0])+pack).hex())
        r = c.post('/api/ops/ingest/remote-id', json=[frame, dict(frame, payload_hex='ff00')]).json()
        assert r['aircraft'] == ['KR-TEST-1'] and len(r['errors']) == 1
        b = runner.buffer
        for k in range(4):
            out = runner.session.step_live(k*0.5, [], [], [(x.node_id, x.rid) for x in b.rid_reports])
        assert [(t['rid'], t['status']) for t in out['tracks']] == [('KR-TEST-1', 'confirmed')]

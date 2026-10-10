"""Remote ID (ASTM F3411 / ASD-STAN Open Drone ID) decoding on the ground station.

The receiver MCU on the dome only forwards what it heard — raw bytes, signal strength, sender address
and receive time (RawRemoteID). Decoding happens here so a spec change or bug never needs a firmware
update, and the raw frames can be kept for later review.

Byte layouts and scaling follow the reference implementation opendroneid-core-c
(libopendroneid/opendroneid.h, Apache-2.0); tests check against vectors produced by that library.
Messages: 0 Basic ID, 1 Location/Vector, 2 Authentication (ignored), 3 Self-ID, 4 System,
5 Operator ID, 0xF Message Pack. Location messages carry no ID, so messages are joined per sender
address until a Basic ID and a valid position are both known.
"""
import argparse
import json
import struct
import time
import urllib.request
from typing import Literal

from pydantic import BaseModel, Field

from ops.core.schemas import RemoteID

MSG_SIZE = 25
BASIC, LOCATION, AUTH, SELF_ID, SYSTEM, OPERATOR_ID, PACK = 0, 1, 2, 3, 4, 5, 0xF
WIFI_OUI = bytes.fromhex('fa0bbc')
APP_CODE = 0x0D                                  # Open Drone ID application code in BT service data / Wi-Fi IE
INV_DIR, INV_SPEED_H, INV_SPEED_V, INV_ALT, INV_TS = 361.0, 255.0, 63.0, -1000.0, 0xFFFF
ID_TYPE = {0: 'none', 1: 'serial', 2: 'caa_registration', 3: 'utm_uuid', 4: 'session_id'}
UA_TYPE = {0: 'none', 1: 'aeroplane', 2: 'multirotor', 3: 'gyroplane', 4: 'hybrid_lift', 5: 'ornithopter', 6: 'glider',
           7: 'kite', 8: 'free_balloon', 9: 'captive_balloon', 10: 'airship', 11: 'parachute', 12: 'rocket',
           13: 'tethered', 14: 'ground_obstacle', 15: 'other'}
STATUS = {0: 'undeclared', 1: 'ground', 2: 'airborne', 3: 'emergency', 4: 'remote_id_failure'}


class RawRemoteID(BaseModel):
    """What the dome MCU forwards for each received Remote ID frame."""
    node_id: str
    received_at: float = Field(description='seconds, shared clock')
    mac: str = Field(description='sender address (BT MAC / Wi-Fi BSSID); joins messages of one aircraft')
    rssi: int | None = None
    transport: Literal['bt4', 'bt5', 'wifi_beacon', 'wifi_nan', 'unknown'] = 'unknown'
    payload_hex: str = Field(description='one 25-byte message or a message pack; BT service data / Wi-Fi IE prefixes allowed')


# ---- decoding -------------------------------------------------------------------

def _alt(v):
    return v*0.5-1000.0


def _str(b):
    return b.split(b'\0', 1)[0].decode('ascii', errors='replace').strip()


def strip_transport(b: bytes) -> bytes:
    """Remove the Wi-Fi vendor IE OUI/type and the app-code + counter bytes if present."""
    if b[:3] == WIFI_OUI and len(b) > 4 and b[3] == APP_CODE:
        b = b[4:]
        return b[1:]                                 # message counter
    if b and b[0] == APP_CODE and (len(b) == MSG_SIZE+2 or (len(b) > 3 and b[2] >> 4 == PACK)):
        return b[2:]                                 # app code + message counter
    return b


def decode_message(m: bytes) -> dict:
    if len(m) < MSG_SIZE:
        raise ValueError(f'message too short: {len(m)} bytes')
    mtype, version = m[0] >> 4, m[0] & 0x0F
    out = dict(type=mtype, version=version)
    if mtype == BASIC:
        out.update(id_type=ID_TYPE.get(m[1] >> 4, m[1] >> 4), ua_type=UA_TYPE.get(m[1] & 0x0F, m[1] & 0x0F), uas_id=_str(m[2:22]))
    elif mtype == LOCATION:
        flags = m[1]
        mult, ew, height_type, status = flags & 1, (flags >> 1) & 1, (flags >> 2) & 1, flags >> 4
        direction, speed_enc, vspeed_enc = m[2], m[3], struct.unpack_from('<b', m, 4)[0]
        lat, lon = struct.unpack_from('<ii', m, 5)
        baro, geo, height = struct.unpack_from('<HHH', m, 13)
        ts = struct.unpack_from('<H', m, 21)[0]
        d = direction+180.0 if ew else float(direction)
        sh = speed_enc*0.75+255*0.25 if mult else speed_enc*0.25
        sv = vspeed_enc*0.5
        out.update(status=STATUS.get(status, status), height_type='ground' if height_type else 'takeoff',
                   direction=None if d >= INV_DIR else d, speed=None if sh >= INV_SPEED_H else sh,
                   vspeed=None if sv >= INV_SPEED_V else sv,
                   lat=None if lat == 0 and lon == 0 else lat/1e7, lon=None if lat == 0 and lon == 0 else lon/1e7,
                   alt_baro=None if baro == 0 else _alt(baro), alt_geo=None if geo == 0 else _alt(geo),
                   height=None if height == 0 else _alt(height),
                   h_accuracy=m[19] & 0x0F, v_accuracy=m[19] >> 4, speed_accuracy=m[20] & 0x0F, baro_accuracy=m[20] >> 4,
                   timestamp=None if ts == INV_TS else ts/10.0, ts_accuracy=m[23] & 0x0F)
    elif mtype == SELF_ID:
        out.update(desc_type=m[1], description=_str(m[2:25]))
    elif mtype == SYSTEM:
        olat, olon = struct.unpack_from('<ii', m, 2)
        count, radius = struct.unpack_from('<HB', m, 10)
        ceiling, floor = struct.unpack_from('<HH', m, 13)
        oalt, stamp = struct.unpack_from('<HI', m, 18)
        out.update(operator_location_type=m[1] & 0x03, classification_type=(m[1] >> 2) & 0x07,
                   operator_lat=None if olat == 0 and olon == 0 else olat/1e7,
                   operator_lon=None if olat == 0 and olon == 0 else olon/1e7,
                   area_count=count, area_radius=radius*10, area_ceiling=_alt(ceiling), area_floor=_alt(floor),
                   category_eu=m[17] >> 4, class_eu=m[17] & 0x0F, operator_alt=None if oalt == 0 else _alt(oalt),
                   timestamp=stamp)                                    # seconds since 2019-01-01 00:00 UTC
    elif mtype == OPERATOR_ID:
        out.update(operator_id_type=m[1], operator_id=_str(m[2:22]))
    elif mtype == AUTH:
        out.update(note='authentication pages are not decoded')
    return out


def decode(payload: bytes) -> list[dict]:
    """Payload (single message or pack, with or without transport prefix) → list of decoded messages.
    Malformed input raises ValueError."""
    try:
        return _decode(payload)
    except (IndexError, struct.error) as e:
        raise ValueError(f'malformed Remote ID payload ({len(payload)} bytes): {e}') from None


def _decode(payload: bytes) -> list[dict]:
    b = strip_transport(payload)
    if not b:
        return []
    if b[0] >> 4 == PACK:
        if len(b) < 3:
            raise ValueError('message pack header too short')
        size, n = b[1], b[2]
        if size != MSG_SIZE or n > 9:
            raise ValueError(f'bad message pack: size={size} count={n}')
        if len(b) < 3+n*MSG_SIZE:
            raise ValueError(f'message pack truncated: {len(b)} bytes for {n} messages')
        return [decode_message(b[3+i*MSG_SIZE:3+(i+1)*MSG_SIZE]) for i in range(n)]
    return [decode_message(b[:MSG_SIZE])]


class Assembler:
    """Joins messages per sender address into RemoteID records."""

    def __init__(self):
        self.state = {}

    def add(self, raw: RawRemoteID):
        """→ (node_id, RemoteID) once a Basic ID and a valid position are known for this sender, else None."""
        s = self.state.setdefault(raw.mac, dict(rssi=None))
        for msg in decode(bytes.fromhex(raw.payload_hex)):
            s[msg['type']] = msg
        s['rssi'], s['node_id'], s['t'] = raw.rssi, raw.node_id, raw.received_at
        basic, loc, system = s.get(BASIC), s.get(LOCATION), s.get(SYSTEM, {})
        if not basic or not loc or loc.get('lat') is None:
            return None
        alt = loc['alt_geo'] if loc.get('alt_geo') is not None else loc.get('alt_baro')
        if alt is None:
            return None
        return raw.node_id, RemoteID(uas_id=basic['uas_id'], lat=loc['lat'], lon=loc['lon'], alt=alt,
                                     speed=loc.get('speed'), heading=loc.get('direction'),
                                     operator_lat=system.get('operator_lat'), operator_lon=system.get('operator_lon'))


# ---- encoding (for tests and the bench sender; mirrors opendroneid-core-c) ------

def encode_basic(uas_id: str, id_type: int = 1, ua_type: int = 2, version: int = 2) -> bytes:
    return bytes([(BASIC << 4) | version, (id_type << 4) | ua_type])+uas_id.encode('ascii')[:20].ljust(20, b'\0')+b'\0'*3


def _enc_alt(a):
    return 0 if a is None else max(0, min(0xFFFF, round((a+1000.0)/0.5)))


def encode_location(lat, lon, alt_geo, speed=None, direction=None, vspeed=None, alt_baro=None, height=None,
                    status=2, height_type=0, timestamp=None, h_acc=0, v_acc=0, speed_acc=0, baro_acc=0, ts_acc=0, version=2) -> bytes:
    if direction is None:
        dir_enc, ew = 181, 1                                        # 361 = invalid
    else:
        direction %= 360
        dir_enc, ew = (round(direction-180), 1) if direction >= 180 else (round(direction), 0)
    if speed is None:
        sp_enc, mult = 255, 1
    elif speed <= 255*0.25:
        sp_enc, mult = round(speed/0.25), 0
    else:
        sp_enc, mult = min(254, round((speed-255*0.25)/0.75)), 1
    vs_enc = 126 if vspeed is None else max(-124, min(124, round(vspeed/0.5)))
    ts = INV_TS if timestamp is None else round(timestamp*10) % 36000
    return (bytes([(LOCATION << 4) | version, (status << 4) | (height_type << 2) | (ew << 1) | mult, dir_enc, sp_enc])
            + struct.pack('<b', vs_enc)+struct.pack('<ii', round(lat*1e7), round(lon*1e7))
            + struct.pack('<HHH', _enc_alt(alt_baro), _enc_alt(alt_geo), _enc_alt(height))
            + bytes([(v_acc << 4) | h_acc, (baro_acc << 4) | speed_acc])+struct.pack('<H', ts)+bytes([ts_acc & 0x0F, 0]))


def encode_pack(messages: list[bytes], version: int = 2) -> bytes:
    return bytes([(PACK << 4) | version, MSG_SIZE, len(messages)])+b''.join(messages)


# ---- bench sender: replay a scenario's cooperative drones as raw frames --------

def main():
    ap = argparse.ArgumentParser(description='Send scenario Remote ID drones to the ops server as raw frames (no hardware needed)')
    ap.add_argument('--server', default='http://localhost:8090')
    ap.add_argument('--rate', type=float, default=1.0, help='frames per second per drone')
    a = ap.parse_args()
    from ops.sources.scenario import generate, replay
    sc = generate()
    for f in replay(sc, dt=1.0/a.rate):
        frames = []
        for node_id, rid in f.rid_reports:
            payload = encode_pack([encode_basic(rid.uas_id), encode_location(rid.lat, rid.lon, rid.alt, speed=rid.speed)])
            frames.append(RawRemoteID(node_id=node_id, received_at=f.t, mac='sim:'+rid.uas_id, rssi=-70, transport='bt5',
                                      payload_hex=(bytes([APP_CODE, 0])+payload).hex()).model_dump())
        if frames:
            req = urllib.request.Request(a.server+'/api/ops/ingest/remote-id', data=json.dumps(frames).encode(),
                                         headers={'Content-Type': 'application/json'}, method='POST')
            with urllib.request.urlopen(req) as r:
                print(f't={f.t:6.1f}', json.load(r))
        time.sleep(1.0/a.rate)


if __name__ == '__main__':
    main()

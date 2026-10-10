"""Run the detector over a video / image folder → CameraDetection JSONL (and optionally to the ops server).

python -m ops.perception.run_video INPUT [--tile 640] [--every 2] [--out detections.jsonl]
                                         [--server http://localhost:8090 --node dome-1 --camera 0]

With --server, detections go to POST /api/ops/ingest together with a fixed NodeStatus for the node
(position/attitude from --node-pos / --attitude) so the server can turn pixels into bearings.
"""
import argparse
import json
import time
import urllib.request
from pathlib import Path

from ops.perception.detector import load_detector
from ops.perception.frames import iter_frames


def run(src, detector, node_id='dome-1', camera_id=0, every=1, fps=10.0, out=None, server=None, node_pos=(0, 0, 120), attitude=(0, 0, 0)):
    lat, n_det, n_frames = [], 0, 0
    fh = open(out, 'w', encoding='utf-8') if out else None
    try:
        for i, t, frame, name in iter_frames(src, fps=fps, every=every):
            t0 = time.perf_counter()
            dets = detector.detect(frame, t, node_id, camera_id)
            lat.append(time.perf_counter()-t0)
            n_frames += 1
            n_det += len(dets)
            if fh:
                for d in dets:
                    fh.write(json.dumps(dict(frame=name, **d.model_dump()), ensure_ascii=False)+'\n')
            if server and dets:
                body = dict(t=t, camera_detections=[d.model_dump() for d in dets],
                            node_statuses=[dict(t=t, node_id=node_id, pos=list(node_pos), attitude=list(attitude), angular_rate=[0, 0, 0])])
                req = urllib.request.Request(server.rstrip('/')+'/api/ops/ingest', data=json.dumps(body).encode(),
                                             headers={'Content-Type': 'application/json'}, method='POST')
                urllib.request.urlopen(req).read()
    finally:
        if fh:
            fh.close()
    ms = sorted(1000*x for x in lat)
    return dict(frames=n_frames, detections=n_det, latency_ms_median=round(ms[len(ms)//2], 1) if ms else None,
                latency_ms_p95=round(ms[int(len(ms)*.95)-1 if len(ms) > 1 else 0], 1) if ms else None)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('input')
    ap.add_argument('--detector', default='skyblob', help='skyblob (light, default) or torchvision')
    ap.add_argument('--arch', default='fasterrcnn_mobilenet_v3_large_fpn')
    ap.add_argument('--tile', type=int, default=None, help='tile size for small objects, e.g. 640')
    ap.add_argument('--min-confidence', type=float, default=0.4)
    ap.add_argument('--every', type=int, default=1, help='use every Nth frame')
    ap.add_argument('--fps', type=float, default=10.0, help='frame rate assumed for image folders')
    ap.add_argument('--out', default=None)
    ap.add_argument('--server', default=None)
    ap.add_argument('--node', default='dome-1')
    ap.add_argument('--camera', type=int, default=0)
    ap.add_argument('--node-pos', type=float, nargs=3, default=(0, 0, 120))
    ap.add_argument('--attitude', type=float, nargs=3, default=(0, 0, 0), help='roll pitch yaw (rad)')
    a = ap.parse_args()
    kw = dict(arch=a.arch) if a.detector == 'torchvision' else {}
    det = load_detector(a.detector, tile=a.tile, min_confidence=a.min_confidence, **kw)
    res = run(a.input, det, a.node, a.camera, a.every, a.fps, a.out, a.server, a.node_pos, a.attitude)
    print(json.dumps(res, ensure_ascii=False))


if __name__ == '__main__':
    main()

import json

import numpy as np
import pytest

from ops.perception.detector import Box, Detector, TiledDetector, nms
from ops.perception.evaluate import ap50, evaluate, read_yolo, size_bin
from ops.perception.run_video import run

SKY = (170, 200, 235)


class DarkBlob(Detector):
    """Test double for a CNN: finds the dark object, but the model input is resized to `net` px,
    so objects smaller than `min_px` after resizing are missed (the small-object problem)."""
    min_confidence = 0.4

    def __init__(self, net=320, min_px=6, label='drone'):
        self.net, self.min_px, self.label = net, min_px, label

    def detect_boxes(self, frame):
        ys, xs = np.where(frame.mean(axis=2) < 60)
        if not len(xs):
            return []
        scale = min(1.0, self.net/max(frame.shape[:2]))
        x1, y1, x2, y2 = xs.min(), ys.min(), xs.max()+1, ys.max()+1
        if min(x2-x1, y2-y1)*scale < self.min_px:
            return []
        return [Box(float(x1), float(y1), float(x2), float(y2), self.label, 0.9)]


def _frame(w=1280, h=720, x=900, y=200, s=10):
    f = np.zeros((h, w, 3), np.uint8)+np.array(SKY, np.uint8)
    f[y:y+s, x:x+s] = 20
    return f


def test_nms_is_class_wise():
    a, b, c = Box(0, 0, 10, 10, 'drone', .9), Box(1, 1, 11, 11, 'drone', .8), Box(1, 1, 11, 11, 'bird', .7)
    assert nms([b, a, c]) == [a, c]


def test_tiling_recovers_small_object():
    f = _frame()
    assert DarkBlob().detect(f, 0, 'dome-1') == []                       # 10 px object shrinks to 2.5 px
    dets = TiledDetector(DarkBlob(), tile=320).detect(f, 0, 'dome-1', 3)
    assert len(dets) == 1 and dets[0].camera_id == 3
    x, y, w, h = dets[0].bbox
    assert (x, y, w, h) == (900, 200, 10, 10) and dets[0].image_size == (1280, 720)


def test_tiles_cover_frame_edges():
    t = TiledDetector(DarkBlob(), tile=320, overlap=0.2)
    ys, xs = zip(*t.tiles(720, 1280))
    assert max(ys)+320 >= 720 and max(xs)+320 >= 1280 and min(ys) == 0 and min(xs) == 0


def test_evaluate_counts_and_size_bins():
    gts = [Box(0, 0, 6, 6, 'drone', 1), Box(100, 100, 140, 140, 'drone', 1), Box(300, 300, 312, 312, 'balloon', 1)]
    preds = [Box(100, 100, 140, 141, 'drone', .9), Box(500, 500, 520, 520, 'drone', .8), Box(300, 300, 312, 312, 'balloon', .3)]
    r = evaluate([(preds, gts)], conf=0.4)
    d = r['classes']['drone']
    assert d['gt'] == 2 and d['precision'] == 0.5 and d['recall'] == 0.5
    assert r['classes']['balloon']['recall'] == 0.0 and r['classes']['balloon']['ap50'] == 1.0   # found, but below threshold
    assert r['recall_by_size_px']['0-8'] == dict(recall=0.0, n=1) and r['recall_by_size_px']['32+'] == dict(recall=1.0, n=1)
    assert r['false_positives_per_frame'] == 1.0


def test_ap50_and_yolo_reader(tmp_path):
    assert ap50([(0.9, True), (0.8, False), (0.7, True)], 2) == pytest.approx(0.5+0.5*(2/3))
    (tmp_path/'a.txt').write_text('1 0.5 0.5 0.1 0.2\n')
    (b,) = read_yolo(tmp_path/'a.txt', 200, 100, ('drone', 'balloon', 'bird'))
    assert b.label == 'balloon' and (b.x1, b.y1, b.x2, b.y2) == pytest.approx((90, 40, 110, 60)) and size_bin(b) == '16-32'


def test_run_video_writes_detections(tmp_path):
    cv2 = pytest.importorskip('cv2')
    path = str(tmp_path/'sky.avi')
    vw = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'MJPG'), 10, (640, 360))
    for k in range(8):
        vw.write(cv2.cvtColor(_frame(640, 360, 100+20*k, 150, 24), cv2.COLOR_RGB2BGR))
    vw.release()
    out = tmp_path/'det.jsonl'
    res = run(path, DarkBlob(net=640), out=str(out))
    rows = [json.loads(l) for l in out.read_text().splitlines()]
    assert res['frames'] == 8 and res['detections'] == 8 and len(rows) == 8
    assert rows[1]['t'] == pytest.approx(0.1) and rows[-1]['bbox'][0] > rows[0]['bbox'][0]


def test_skyblob_finds_dark_and_bright_targets_and_ignores_buildings():
    from ops.perception.detector import SkyBlobDetector
    rng = np.random.default_rng(0)
    H, W = 540, 960
    sky = (190-30*np.linspace(0, 1, H)[:, None])+rng.normal(0, 2, (H, W))
    sky[100:104, 200:204] -= 40                                   # 4 px dark target
    sky[150:170, 600:620] += 40                                   # 20 px bright target
    sky[H-120:] = 80+70*rng.random((120, W))+(np.indices((120, W))[1] % 40 < 20)*30   # buildings
    img = np.repeat(np.clip(sky, 0, 255).astype(np.uint8)[:, :, None], 3, axis=2)
    dets = SkyBlobDetector().detect(img, 0, 'dome-1')
    assert all(d.label == 'unknown' for d in dets)
    centres = [(d.bbox[0]+d.bbox[2]/2, d.bbox[1]+d.bbox[3]/2) for d in dets]
    assert any(abs(x-202) < 3 and abs(y-102) < 3 for x, y in centres)
    assert any(abs(x-610) < 3 and abs(y-160) < 3 for x, y in centres)
    assert not any(y > H-120 for _, y in centres)                 # nothing on the textured strip


def test_synthetic_eval_runs_small():
    from ops.perception.synth_eval import run
    r = run(frames=4, W=1920, H=1080, noise=2.0)
    rec = list(r['recall_by_contrast_then_size']['40'].values())
    assert min(rec) >= 0.5 and sum(rec)/len(rec) >= 0.9          # one target sits in front of the small cloud
    assert r['false_alarms_per_frame'] <= 5                       # smoke bound for 4 HD frames; see synth_eval for figures


def test_unknown_label_pairs_with_any_in_triangulation():
    from ops.core.schemas import Detection, Measurement
    from ops.localization.triangulate import triangulate
    from ops.perception.bearing import ray_to_bearing
    sig = np.radians(0.3)
    def b(node, label):
        az, el = ray_to_bearing(np.array([150, 120, 150.])-np.array(node))
        return Detection(t=0, node_id=str(node), node_pos=node, source='camera', label=label, confidence=.8,
                         measurement=Measurement(kind='bearing', z=[az, el], R=[[sig**2, 0], [0, sig**2]]))
    fixes, _ = triangulate([b((0, 0, 100), 'unknown'), b((300, 0, 100), 'drone')])
    assert len(fixes) == 1 and fixes[0].detection().label == 'drone'

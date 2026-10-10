"""Wires steps ①–⑥ for each time step. The RAG card (⑦) is requested separately,
so a slow recommendation never delays the alert.

① nodes.status → ② perception.bearing → ③ localization.triangulate
→ ④ tracking (manager + fusion with Remote ID) → ⑤ assessment.classify → ⑥ assessment.threat
"""
from dataclasses import dataclass

import numpy as np

from ops.assessment import threat as threat_
from ops.assessment.classify import WindowClassifier
from ops.core.reference import Reference
from ops.core.schemas import Detection, Measurement
from ops.localization.triangulate import triangulate
from ops.nodes.status import NodeMonitor
from ops.perception.bearing import to_bearing
from ops.tracking.manager import TrackManager

RID_SIGMA = (5.0, 5.0, 10.0)     # m, GNSS self-report uncertainty (E, N, U)


def rid_detection(t, node_id, node_pos, rid, enu) -> Detection:
    z = enu.to_enu(rid.lat, rid.lon, rid.alt)
    return Detection(t=t, node_id=node_id, node_pos=node_pos, source='remote_id', rid=rid,
                     measurement=Measurement(kind='position', z=z.tolist(), R=np.diag(np.square(RID_SIGMA)).tolist()))


@dataclass
class StepResult:
    t: float
    nodes: list
    bearings: list
    bearing_only: list
    fixes: list
    tracks: list
    threats: list


class Pipeline:
    def __init__(self, cameras, enu, reference: Reference | None = None, ref_range_m: float | None = None):
        self.cameras, self.enu = cameras, enu
        self.reference = reference or Reference()
        self.monitor = NodeMonitor(ref_range_m or 0.4*cameras[0].fx/8)
        self.tracker = TrackManager()
        self.classifier = WindowClassifier()

    def step(self, t: float, node_statuses, camera_detections, rid_reports, wind=None) -> StepResult:
        nodes = {s.node_id: self.monitor.evaluate(s) for s in node_statuses}
        bearings = [b for d in camera_detections
                    if d.node_id in nodes and (b := to_bearing(d, nodes[d.node_id], self.cameras[d.camera_id])) is not None]
        fixes, bearing_only = triangulate(bearings)
        positions = [f.detection() for f in fixes]
        # Remote ID carries its own position, so it is used even if that node sent no status this step
        positions += [rid_detection(t, nid, nodes[nid].pos if nid in nodes else (0.0, 0.0, 0.0), rid, self.enu) for nid, rid in rid_reports]
        tracks = self.tracker.step(t, positions)
        threats = []
        if wind is not None:
            tracks = [self.classifier.update(tr, wind, self.reference.permits) if tr.status == 'confirmed' else tr for tr in tracks]
            self.classifier.forget({tr.track_id for tr in tracks})
            threats = sorted((threat_.evaluate(tr, wind, self.reference) for tr in tracks if tr.status == 'confirmed'),
                             key=lambda x: -x.score)
        return StepResult(t, list(nodes.values()), bearings, bearing_only, fixes, tracks, threats)

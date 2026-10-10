import numpy as np

from ops.core.schemas import CameraDetection, NodeStatus
from ops.nodes.status import NodeMonitor
from ops.perception.bearing import Camera, bearing_to_ray, pixel_ray, project, to_bearing


def _status(att=(0, 0, 0), rate=(0, 0, 0)):
    return NodeStatus(t=0, node_id='n', pos=(0, 0, 100), attitude=att, angular_rate=rate)


def test_node_stability_drops_with_shake():
    calm, shaky = NodeMonitor(300), NodeMonitor(300)
    for _ in range(10):
        a = calm.evaluate(_status((0.01, 0, 0), (0.02, 0, 0)))
        b = shaky.evaluate(_status((0.3, 0.2, 0), (0.8, 0.5, 0)))
    assert a.stability > 0.9 > 0.2 > b.stability
    assert b.coverage_m < a.coverage_m


def test_pixel_centre_maps_to_camera_axis():
    cam = Camera(mount_yaw_deg=0, mount_pitch_deg=0)
    d = pixel_ray(cam.cx, cam.cy, (0, 0, 0), cam)
    assert np.allclose(d, [1, 0, 0], atol=1e-9)          # body x = east when yaw = 0


def test_bearing_corrected_by_dome_attitude():
    cam = Camera(mount_yaw_deg=30, mount_pitch_deg=10)
    node, target = np.array([0, 0, 100.]), np.array([400, 250, 160.])
    truth = (target-node)/np.linalg.norm(target-node)
    for att in [(0, 0, 0), (0.2, -0.15, 0.3), (-0.3, 0.1, -0.2)]:
        u, v = project(target, node, att, cam)
        det = CameraDetection(t=0, node_id='n', bbox=(u-5, v-5, 10, 10), image_size=(cam.width, cam.height),
                              label='drone', confidence=0.9)
        b = to_bearing(det, _status(att), cam)
        assert np.degrees(np.arccos(bearing_to_ray(*b.measurement.z)@truth)) < 1e-6


def test_low_confidence_detections_dropped():
    cam = Camera()
    det = CameraDetection(t=0, node_id='n', bbox=(10, 10, 5, 5), image_size=(cam.width, cam.height), label='bird', confidence=0.2)
    assert to_bearing(det, _status(), cam) is None

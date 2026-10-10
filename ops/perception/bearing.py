"""Pixel → world bearing using camera intrinsics and the dome attitude (IMU) at frame time.

Frames: world ENU; dome body FLU (x forward, y left, z up), R_world_body = Rz(yaw)·Ry(pitch)·Rx(roll)
with yaw counter-clockwise from east; camera OpenCV (x right, y down, z forward), mounted at
(mount_yaw, mount_pitch) in the body frame. Bearing = [azimuth from north clockwise, elevation].
"""
from dataclasses import dataclass, field

import numpy as np

from ops.core.schemas import Detection, Measurement


@dataclass
class Camera:
    width: int = 3840
    height: int = 2160
    hfov_deg: float = 60.0
    mount_yaw_deg: float = 0.0
    mount_pitch_deg: float = 0.0
    pixel_sigma: float = 1.5
    fx: float = field(init=False)

    def __post_init__(self):
        self.fx = self.width/2/np.tan(np.radians(self.hfov_deg)/2)
        self.cx, self.cy = self.width/2, self.height/2

    @property
    def R_body_cam(self):
        y, p = np.radians(self.mount_yaw_deg), np.radians(self.mount_pitch_deg)
        f = np.array([np.cos(p)*np.cos(y), np.cos(p)*np.sin(y), np.sin(p)])
        r = np.array([np.sin(y), -np.cos(y), 0.0])
        return np.column_stack([r, np.cross(f, r), f])


def R_world_body(attitude):
    roll, pitch, yaw = attitude
    cr, sr, cp, sp, cy, sy = np.cos(roll), np.sin(roll), np.cos(pitch), np.sin(pitch), np.cos(yaw), np.sin(yaw)
    Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    Ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    Rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    return Rz@Ry@Rx


def ray_to_bearing(d):
    e, n, u = d
    return np.array([np.arctan2(e, n), np.arctan2(u, np.hypot(e, n))])


def bearing_to_ray(az, el):
    return np.array([np.sin(az)*np.cos(el), np.cos(az)*np.cos(el), np.sin(el)])


def project(point, node_pos, attitude, cam: Camera):
    """World point → pixel (u, v), or None when behind the camera or outside the frame."""
    c = cam.R_body_cam.T@R_world_body(attitude).T@(np.asarray(point, float)-np.asarray(node_pos, float))
    if c[2] <= 0:
        return None
    u, v = cam.fx*c[0]/c[2]+cam.cx, cam.fx*c[1]/c[2]+cam.cy
    if not (0 <= u < cam.width and 0 <= v < cam.height):
        return None
    return u, v


def pixel_ray(u, v, attitude, cam: Camera):
    c = np.array([(u-cam.cx)/cam.fx, (v-cam.cy)/cam.fx, 1.0])
    d = R_world_body(attitude)@cam.R_body_cam@c
    return d/np.linalg.norm(d)


def to_bearing(det, node_status, cam: Camera, imu_sigma_rad: float = np.radians(0.5),
               sync_s: float = 0.01, min_confidence: float = 0.4):
    """CameraDetection + NodeStatus at frame time → bearing Detection, or None if confidence is too low.

    σ combines pixel noise, IMU attitude error and attitude change during the sync error.
    """
    if det.confidence < min_confidence:
        return None
    x, y, w, h = det.bbox
    d = pixel_ray(x+w/2, y+h/2, node_status.attitude, cam)
    az, el = ray_to_bearing(d)
    rate = float(np.linalg.norm(node_status.angular_rate))
    sigma = float(np.sqrt((cam.pixel_sigma/cam.fx)**2+imu_sigma_rad**2+(rate*sync_s)**2))
    R = [[(sigma/max(np.cos(el), .2))**2, 0.0], [0.0, sigma**2]]
    return Detection(t=det.t, node_id=det.node_id, node_pos=node_status.pos, source='camera',
                     measurement=Measurement(kind='bearing', z=[float(az), float(el)], R=R),
                     label=det.label, confidence=det.confidence)

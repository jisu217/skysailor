"""Data contracts shared by dome nodes, the ground-station pipeline, RAG and the UI.

Coordinates inside the pipeline are local ENU metres (see ops.core.geo). Lat/lon only
appears at the edges (sensor input, map output). See ops/docs/DESIGN.md §4.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Vec3 = tuple[float, float, float]
TargetClass = Literal['drone', 'balloon', 'bird', 'unknown']
ThreatLevel = Literal['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
# Escalation ladder, lowest to highest (rag/docs/DESIGN.md §4).
Action = Literal['observe', 'report', 'alert', 'rf_jam', 'kinetic']


class _Model(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


# ---- input: ① dome node -------------------------------------------------------

class NodeStatus(_Model):
    """Dome node telemetry (GPS + IMU) and the observation quality derived from it."""
    t: float
    node_id: str
    pos: Vec3 = Field(description='ENU position (m)')
    attitude: Vec3 = Field(description='roll, pitch, yaw (rad); used to turn pixels into bearings')
    angular_rate: Vec3 = Field(description='rad/s; camera shake indicator')
    battery: float | None = None
    link_quality: float | None = None
    camera_ok: bool = True
    stability: float | None = Field(None, ge=0, le=1, description='filled by ops.nodes.status')
    coverage_m: float | None = Field(None, description='filled by ops.nodes.status')


class RemoteID(_Model):
    uas_id: str
    lat: float
    lon: float
    alt: float
    speed: float | None = None
    heading: float | None = None
    operator_lat: float | None = None
    operator_lon: float | None = None


class CameraDetection(_Model):
    """One object found in one frame by ops.perception.detector (pixel space)."""
    t: float
    node_id: str
    camera_id: int = 0
    bbox: tuple[float, float, float, float] = Field(description='x, y, w, h (px)')
    image_size: tuple[int, int]
    label: Literal['drone', 'balloon', 'bird', 'unknown'] = Field(description="'unknown' from class-agnostic detectors; ⑤ decides")
    confidence: float = Field(ge=0, le=1)


# ---- input: ② → ③ common measurement -----------------------------------------

class Measurement(_Model):
    """What was measured plus its noise covariance R.

    kind='bearing'  z=[az, el] (rad, from node_pos)  camera detection after ops.perception.bearing
    kind='position' z=[e, n, u] (m)                  Remote ID self-report, or ops.localization output
    """
    kind: Literal['position', 'bearing'] = 'position'
    z: list[float]
    R: list[list[float]]


class Detection(_Model):
    t: float = Field(description='seconds, shared clock')
    node_id: str
    node_pos: Vec3 = Field(description='sensor node ENU position (m)')
    measurement: Measurement
    source: Literal['camera', 'remote_id', 'external']
    label: Literal['drone', 'balloon', 'bird', 'unknown'] | None = Field(None, description='camera classifier output')
    confidence: float | None = None
    rid: RemoteID | None = None


class WindEstimate(_Model):
    t: float
    w: Vec3
    P: list[list[float]] = Field(description='3x3 covariance (m/s)^2')
    source: Literal['dome', 'station', 'sim'] = 'sim'


# ---- analysis -----------------------------------------------------------------

class ClassProbs(_Model):
    drone: float = .25
    balloon: float = .25
    bird: float = .25
    unknown: float = .25


class Track(_Model):
    track_id: str
    status: Literal['tentative', 'confirmed', 'lost']
    t: float
    pos: Vec3
    vel: Vec3
    P: list[list[float]] = Field(description='6x6 state covariance [pos, vel]')
    classes: ClassProbs = Field(default_factory=ClassProbs)
    rid: RemoteID | None = None
    sources: list[Literal['camera', 'remote_id', 'external']] = Field(default_factory=list)
    image_label: ClassProbs | None = Field(None, description='averaged camera classifier output')
    permitted: bool | None = Field(None, description='Remote ID found on the permit list')
    class_basis: list[str] = Field(default_factory=list, description='human-readable reasons for classes')
    check: bool = Field(False, description='cues disagree; operator should look')
    history: list[Vec3] = Field(default_factory=list)


class Factor(_Model):
    name: str
    value: str
    contribution: float


class Threat(_Model):
    track_id: str
    score: float = Field(ge=0, le=100)
    level: ThreatLevel
    p_hostile: float
    consequence: float
    urgency: float
    cpa_m: float | None = None
    tti_s: float | None = None
    zone_id: str | None = None
    impact: tuple[float, float] | None = Field(None, description='balloon landing estimate (ENU e, n)')
    impact_radius_m: float | None = None
    fall_time_s: float | None = None
    factors: list[Factor] = Field(default_factory=list)


# ---- recommendation (RAG) -----------------------------------------------------

class Citation(_Model):
    chunk_id: str
    doc: str
    article: str
    quote: str
    verified: bool = False


class CaseRef(_Model):
    """A similar past gray-zone case and what was done about it."""
    case_id: str
    title: str
    date: str
    actions_taken: list[str]
    outcome: str
    constraints: list[str] = Field(default_factory=list)
    similarity: float
    matched_on: list[str] = Field(default_factory=list, description='situation fields that matched')
    source: str


class Constraint(_Model):
    kind: Literal['legal', 'operational']
    text: str
    applies_to: list[Action] = Field(default_factory=list)
    citation: Citation | None = None


class Recommendation(_Model):
    """Three-part card: similar cases / legal & operational constraints / recommended level."""
    track_id: str
    mode: Literal['template', 'llm'] = 'template'
    country: str = 'kr'
    index_version: str
    similar_cases: list[CaseRef] = Field(default_factory=list)
    constraints: list[Constraint] = Field(default_factory=list)
    recommended_action: Action = 'observe'
    allowed_range: list[Action] = Field(default_factory=lambda: ['observe'])
    action_status: dict[str, Literal['allowed', 'conditional', 'excluded', 'out']] = Field(default_factory=dict)
    deadline_s: float | None = None
    justification: str = ''
    evidence_sufficient: bool = False
    notice: str = 'AI는 선택지와 근거만 제시합니다. 최종 결정과 실행은 운용자가 합니다.'


# ---- decision -----------------------------------------------------------------

class Decision(_Model):
    track_id: str
    t: float
    operator: str
    decision: Literal['approve', 'hold', 'observe_more', 'dismiss']
    action: Action | None = None
    override_reason: str | None = Field(None, description='required when differing from recommended_action')
    snapshot_ref: str | None = None

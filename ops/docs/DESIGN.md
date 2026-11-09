# ops Technical Design

Scope: 정의서 ①–⑥·⑧ 단계. 대응 card의 내용(유사 사례·제약·권고 수위)은 [rag/docs/DESIGN.md](../../rag/docs/DESIGN.md) 참고.
사용법과 현재 상태는 [ops/README.md](../README.md) 참고.

## 목차

1. [Problem Statement](#1-problem-statement)
2. [Design Principles](#2-design-principles)
3. [System Architecture](#3-system-architecture)
4. [Data Model](#4-data-model)
5. [Components](#5-components)
6. [Evaluation](#6-evaluation)
7. [Design Decisions](#7-design-decisions)
8. [Limitations](#8-limitations)
9. [Open Issues](#9-open-issues)

---

## 1. Problem Statement

도심 환경에서 소형 드론·풍선 등 저신호 비행체를 탐지, 추적, 식별하고 위협도를 평가하여 대응 결심을 지원하는 Gray-zone Counter-UAS 체계를 개발하라.

- Input: dome node의 camera 영상, Remote ID, 자세·위치(GPS·IMU), 바람, 사전 참조 정보(보호시설·인구·허가 목록).
- Output: 표적별 궤적·유형·위협도와 그 근거, 결정 마감 시각, 운용자 결정 기록.
- Requirements: 같은 입력이면 같은 판단(재현성), 모든 판단에 근거 표시, 대응 추천이 늦어도 경보는 지연 없음.

---

## 2. Design Principles

- UI-first: 단순한 분석으로 화면까지 end-to-end 동작을 먼저 확보한 뒤 분석 고도화.
- Deterministic: 위협도는 고정 규칙으로 계산. LLM은 판단에 관여하지 않음.
- Explainable: 식별·위협도 결과에 판단 근거를 항상 함께 표시.
- Decoupled alerting: 위협도 계산과 RAG card 생성을 분리. RAG 지연과 무관하게 경보 발생.
- Human-in-the-loop: AI는 선택지와 근거만 제시하고 실행 권한 없음.

---

## 3. System Architecture

| Screen | Stage | Method | Owner |
|---|---|---|---|
| 1. 기기 성능 | ① Node status | Remote ID 수신, camera 촬영 | Dome firmware(sensor 팀) |
| | | 무게추 자세 제어 | 기존 코드(`hanging.py`, Arena) |
| | | Node 안정도 평가, 바람 추정 | `ops/nodes/` |
| 2. 표적 판단 | ② Detection | 하늘 영역 대비 검출, camera 방향 보정 | `ops/perception/` |
| | ③ Localization | Triangulation | `ops/localization/` |
| | ④ Tracking | Kalman filter, data association, sensor fusion | `ops/tracking/` |
| | ⑤ Identification | 바람 대비 운동 + Remote ID 허가 확인(+ 선택적 영상 분류) | `ops/assessment/classify.py` |
| | ⑥ Threat | 위협도 점수화, 풍선 낙하 예측 | `ops/assessment/threat.py`, `footprint.py` |
| 3. 대응 결심 | ⑦ Recommendation | 오프라인 RAG, 대응 수위 단계표 | `rag/` |
| | ⑧ Decision | 결정 마감, 사람 결정과 감사 기록 | `ops/service/` |

```
Dome ──video──▶ ② detect → bearing ─┐
     ──IMU────▶ (attitude correction)├─▶ ③ triangulate → ④ track ◀── Remote ID (direct position)
     ──GPS────▶ ① node status       ─┘                      │
                                                            ▼
                                   ⑤ identify → ⑥ threat ──▶ UI (alert)
                                                            └──▶ ⑦ rag card → ⑧ operator decision → log
```

Cooperative vs. non-cooperative targets

- Cooperative(허가 drone): Remote ID로 자기 위치를 직접 송신. ②③을 거치지 않고 ④로 바로 입력.
- Non-cooperative(위협 drone·풍선): Remote ID 없음. Camera 기반 ② → ③으로 위치 획득.

---

## 4. Data Model

### 4.1 Inputs

| Type | Source | Fields | Rate |
|---|---|---|---|
| A. Node status | Dome GPS·IMU | 위치, 자세(roll·pitch·yaw), 각속도, 배터리, 통신 품질, camera 상태 | 10 Hz |
| B1. Camera | Dome camera → 지상 | 영상 frame(또는 압축 frame) | 5–15 fps |
| B2. Remote ID | Dome 수신기 | 기체 ID, 위치·고도·속도·방향, 운용자 위치 | 수신 시 |
| C. Environment | Dome 표류, 기상 관측소 | 풍향·풍속, 추정 오차 | 10 s – 1 min |
| D. Reference | 사전 준비 | 보호시설(위치·반경·중요도), 인구 격자, 허가 비행 목록, 공역, 지도 | 고정 |
| E. Operator | 화면 | 결정, 사유, 추가 관측 요청 | 수시 |

### 4.2 Coordinate System

- 내부 계산은 기준점 원점의 ENU(East-North-Up) 미터 좌표계. 위경도 변환은 입력과 지도 출력 단계에서만 수행(`ops/core/geo.py`).
- 방향은 방위각(북 기준 시계 방향)과 고각(수평 기준 상향)으로 표현.

### 4.3 Schemas (`ops/core/schemas.py`)

| Schema | Producer → Consumer | Key fields |
|---|---|---|
| `NodeStatus` | Dome → ①, ② | 위치, 자세, 각속도, 안정도, 관측 범위 |
| `CameraDetection` | ② 검출 → ② 방향 변환 | bbox(px), 유형, confidence |
| `Detection` | ② / Remote ID → ③ ④ | 측정값(방향 또는 위치 + 공분산 R), 출처, 유형, Remote ID |
| `WindEstimate` | 바람 → ⑤ ⑥ | `w`, `P`(불확실성) |
| `Track` | ④ → ⑤ ⑥ UI | 위치, 속도, 공분산, 출처, 영상 유형, 분류 확률 |
| `Threat` | ⑥ → UI·rag | 점수, 단계, 세 요소, CPA, TTI, 근거 |
| `Recommendation` | rag → UI | 유사 사례, 제약, 권고 수위 |
| `Decision` | UI → 기록 | 결정, 대응, 사유 |

---

## 5. Components

### 5.1 ① Node Status (`ops/nodes/`)

Dome 자세 제어는 dome 측 담당(기존 `hanging.py` model, Arena 제어기). ops는 수신한 상태로 해당 node의 관측 신뢰도를 평가.

| Output | Computation |
|---|---|
| Stability (0–1) | 최근 기울기와 각속도(camera 흔들림) 기반 |
| Coverage | Camera 탐지 거리 × 안정도 |
| Node alerts | 안정도 저하, camera 이상, 통신 품질 저하 |
| Wind (`wind.py`) | 무동력 dome의 수평 표류 속도 ≈ 해당 고도 풍속. 관측소 자료와 결합 |

안정도는 ② 방향 오차와 ③ 위치 오차에 직접 반영. 즉 자세 제어 성능이 탐지·위치 정확도로 이어지는 연결 고리.

### 5.2 ② Detection (`ops/perception/`)

Approach. system의 핵심은 결심지원이므로 검출은 "하늘의 특정 지점에 무언가 있음"만 알리는 경량 단계로 한정. 종류 판단은 ⑤ Identification(바람 대비 운동 + Remote ID)이 담당. 학습 data·GPU 불필요.

Detectors (`detector.py`)

| Detector | Method | Classes | Dependency | 4K frame |
|---|---|---|---|---|
| `SkyBlobDetector` (default) | 하늘 영역에서 배경 대비 어둡거나 밝은 소형 blob 검출 | `unknown` | OpenCV | ~0.2 s (CPU) |
| `TorchvisionDetector` (optional) | COCO 사전학습 model(bird→조류, kite→풍선, airplane→drone 임시 매핑) | 3 | torch·torchvision | 0.5–8 s |

`SkyBlobDetector` pipeline:

1. Sky mask: 1/4 해상도에서 표적 크기 이하 구조 제거(closing·opening) 후, 국소 표준편차가 낮은 매끈한 영역만 하늘로 판정. 원본 대비 차이가 넓게 분포한 영역(건물·수목 texture)은 제외.
2. Background contrast: black-hat(어두운 표적)과 top-hat(밝은 표적)을 분리 계산. 합산 시 한쪽 잔상이 반대 성질 표적과 결합되는 문제 방지.
3. Threshold: 하늘 잔차 median + 6 × robust std, 최소 gray level 10.
4. Filtering: 크기 2–64 px, 더 강한 반대 성질 표적 인접 잔상 제거, half-threshold 기준 대형 구조(구름 경계 등)에 속한 조각 제거.

Bearing conversion (`bearing.py`)

```
bbox center pixel → camera ray (intrinsics)
                  → rotate by mount angle + dome attitude at capture time (IMU)
                  → azimuth · elevation [az, el]
```

- 영상 frame과 IMU 값은 동일 시각 기준 필요(time sync, §9).
- 방향 공분산 R은 pixel 오차와 자세 오차(흔들림)의 합성.

Tools

| File | Purpose |
|---|---|
| `perception/run_video.py` | 동영상·이미지 → 검출 결과 JSONL. `--server` 지정 시 server ingest 경로로 전송 |
| `perception/evaluate.py` | YOLO 형식 정답 대비 precision·recall·AP50, 크기별 recall, frame당 false alarm(`SkyBlobDetector`는 class-agnostic 평가) |
| `perception/synth_eval.py` | 합성 하늘(gradient·noise·구름·건물)에 크기·대비를 아는 표적을 삽입해 측정 |

### 5.3 ③ Localization (`ops/localization/`)

Camera는 방향만 측정하고 거리는 측정 불가. 따라서 2개 이상 node의 방향선 교차점을 위치로 계산.

1. Grouping: 동일 시간대(0.5 s 이내)·동일 유형의 방향선을 같은 표적 후보로 묶음.
2. Intersection: 방향선까지 거리 제곱합을 최소화하는 점을 least squares로 계산. 위치 공분산과 잔차 함께 출력.
3. Rejection: 방향선이 거의 평행(교차각 작음)하면 위치 오차 과대로 기각.
4. Single node: node 1대만 관측 시 "해당 방향 어딘가"로 처리하고 화면에 방향선으로 표시. 위협도는 위치 확보 시점부터 계산.

### 5.4 ④ Tracking (`ops/tracking/`)

| Component | Method |
|---|---|
| Filter (`kalman.py`) | Constant-velocity Kalman filter. 입력은 ③ 위치 또는 Remote ID 위치 |
| Association (`association.py`) | 예측 위치 기준 Mahalanobis gating 후 nearest-first 배정 |
| Track management (`manager.py`) | 최근 5회 중 3회 검출 시 confirm, 5 s 무측정 시 drop |
| Fusion (`fusion.py`) | Camera 궤적이 Remote ID 위치와 반복적으로 근접하면 동일 기체로 병합 → 허가 여부 확인 |

### 5.5 ⑤ Identification (`ops/assessment/classify.py`)

세 가지 근거를 결합해 유형 확률 산출.

| Evidence | Description | Strength |
|---|---|---|
| Visual class (optional) | ② 유형·confidence의 궤적 단위 평균. 기본 검출기(class 없음)에서는 미사용 | 형상 기반 즉시 구분 |
| Wind-relative motion | `v_air = v_track − w`, `T = v_airᵀ(P_v + P_w)⁻¹v_air`. 최근 5 s 평균 T가 작으면 바람 추종 → 풍선, 크면 자력 비행 → Drone으로 가정 | 영상 없이 풍선/동력 비행체 구분 |
| Remote ID | 신호 수신 + 허가 목록 등재 시 허가 drone | 신원 확정 |

- 세 근거를 독립 확률로 보고 곱으로 결합(Naive Bayes). 근거 수가 적을수록 "unknown" 비중을 크게 유지(근거 0개 100%, 1개 35%, 2개 12%, 3개 5%).
- 영상 근거와 운동 근거가 상충하면 "확인 필요"로 표시하고 양쪽 근거를 모두 노출.
- 운동 근거는 최근 5 s 누적 후 사용. 그 전에는 "판정 대기".
- 운동 근거만으로는 drone과 조류를 구분하지 않음. 평활 속도의 방향 변화량 측정 결과 drone(0.054–0.089 rad/0.5 s)과 조류(0.069–0.071)의 분포가 겹침. 따라서 자력 비행 표적은 drone으로 가정. 조류의 drone 오인은 오경보 증가로 이어지나 운용자가 해제 가능한 반면, drone의 조류 오인은 위협 누락으로 직결되기 때문.
- 판정 근거는 문장으로 `Track.class_basis`에 저장해 화면에 그대로 표시.

### 5.6 ⑥ Threat Assessment (`ops/assessment/threat.py`, `footprint.py`)

```
Threat = P(hostile) × Consequence × Urgency     → 0–100

P(hostile)   ← 분류 결과, Remote ID 유무, 허가 비행 여부
Consequence  ← 최근접 보호시설 중요도, 예상 도달·낙하 지점 인구 밀집도
Urgency      ← CPA(최근접 거리), TTI(보호구역 도달까지 남은 시간)
```

CPA / TTI (직선 운동 가정). 표적 위치 `p`, 속도 `v`, 보호구역 중심 `c`, 반경 `r`에 대해

```
t_cpa = max(0, −(p−c)·v / ‖v‖²)
CPA   = ‖(p−c) + v·t_cpa‖
TTI   = min t ≥ 0 such that ‖(p−c) + v·t‖ = r   (도달하지 않으면 ∞)
```

Balloon footprint.

```
낙하 예상 지점 ≈ 현재 위치 + 바람 × (고도 / 하강 속도)
반경            ∝ 바람 불확실성 × 낙하 시간
```

원 내부 인구를 Consequence에 반영.

Track initialization guard. 생성 직후 궤적은 속도 추정이 불안정해 TTI가 과소 추정될 수 있음. 수평 속도 불확실성이 3 m/s 초과 시 접근 방향을 배제하고 위치만으로 평가("속도 추정 중"), 수직 속도 불확실성이 0.5 m/s 초과 시 풍선 하강 속도를 기본값(1 m/s)으로 고정.

Score. `100 × (P × C × U)^0.7`. 저점수 구간을 넓혀 단계 간 변별력 확보.

Threat levels (초기값, 팀 검토로 조정)

| Level | Score | UI |
|---|---|---|
| LOW | 0–25 | 회색 |
| MEDIUM | 25–50 | 노랑 |
| HIGH | 50–75 | 주황 + 경보 + 결정 대기열 |
| CRITICAL | 75–100 | 빨강 + 경보 + 결정 대기열 최상단 |

### 5.7 ⑦ Recommendation · ⑧ Decision (`ops/service/`)

- ⑦: HIGH 이상 표적의 상황 요약을 rag에 전달하고 유사 사례·제약·권고 수위를 담은 card 수신. Card는 상황 key 단위로 cache해 같은 상황에서 같은 card 보장. 상세는 rag 설계 문서 참고.
- Decision deadline: `TTI − margin`(drone 60 s, 풍선 120 s)을 화면에 표시.
- ⑧ Decision log (`decisions.py`): 결정 1건당 JSONL 1행으로 `outputs/ops/decisions.jsonl`에 기록.
  - 결정, 대응, 시각, 첫 경보부터 결정까지 소요 시간
  - 결정 시점의 위협도와 card(rag index version 포함)
  - 권고와 다른 결정 시 override 사유(필수 입력)
- Audit integrity: 기록되는 위협도·card는 client 전송값이 아닌 Server가 해당 track에 마지막으로 표시한 snapshot 기준. Snapshot 부재 시 404, track 불일치 시 409로 거부.

### 5.8 UI (`prototypes/c-uas-ops.html`)

| Screen | Question | Content |
|---|---|---|
| Main | 현재 상황은? | 세 화면 요약 card, 상황도, event feed |
| 1. 기기 성능 | 잘 관측 중인가? | Node별 안정도·기울기·관측 범위, 탑재 제어기(Arena 근거), 바람 |
| 2. 표적 판단 | 무엇이고 얼마나 위험한가? | 상황도(궤적·방향선·낙하 범위), 위험도순 목록, 식별 근거, 위협도 3요소 |
| 3. 대응 결심 | 무엇을 언제까지 해야 하나? | 마감순 결정 대기열, 유사 사례, 제약, 대응 단계표, 부수 피해, 결정 button, 결정 기록 |

상단 바에 처리 단계, 경보 수, 최단 잔여 시간(golden time) 상시 표시.

Decision queue persistence. track 소실·재획득이나 일시적 위협 단계 하락 시에도 운용자가 보던 card 유지.

- 대기열에 진입한 표적은 결정 완료 또는 마지막 경보 후 30 s 경과 시까지 유지. 소실 중에는 "추적 끊김 · n초" 표시와 함께 마지막 card 노출.
- 소실 표적 250 m 이내에서 30 s 안에 새 경보 표적 발생 시 동일 표적으로 연결 표시("T-009 (이전 T-003)"). 결정 소요 시간은 최초 경보 기준. 새 track 식별 완료 전까지 이전 판정과 card 유지.
- 근본 원인은 tracking 단계의 track 단절(소형·고정익 drone 추적 유지율 약 50%, §6.2). tracking 단계의 re-identification은 최적화 단계 과제.

---

## 6. Evaluation

### 6.1 Setup

| Item | Value |
|---|---|
| Nodes | Dome 3대, 정삼각형 배치, 간격 250 m / 700 m |
| Cameras | Dome당 8대, 4K, HFOV 60°, 수평 5°·상향 38° 2단 |
| Scenario | 120 s, seed 0, 가상 검출 model(표적 크기 → Pixel 크기 → 검출 확률) |
| Reference | 가상 보호구역 2곳(정부청사·변전소), 인구 밀집 2곳, 허가 목록에 R-01 |

| Target | Metric |
|---|---|
| 좌표 변환 | 왕복 변환 오차 |
| 방향 변환 | 기지 위치 물체의 계산 방향 정확도, 자세 보정 유무 비교 |
| Triangulation | 교차 위치 오차, 저교차각 기각 여부 |
| Tracking | 직선 표적 수렴, 교차 표적 ID swap 여부 |
| Fusion | Camera 궤적과 Remote ID의 정상 병합 여부 |
| Identification | 풍선·drone·조류 정확도, 근거 조합별 비교 |
| Threat | CPA·TTI 정확도, 접근 시 점수 단조 증가, Remote ID 허가 시 점수 하락 |
| End-to-end | Scenario별 탐지율, 위치 오차, 최고 위험 표적 1순위 여부, 탐지→card 소요 시간 |

### 6.2 Tracking & Localization

지표: 표적 50 m 이내에 confirmed track이 존재한 시간 비율 / 위치 오차 median.

| Target | Spacing 250 m | Spacing 700 m |
|---|---|---|
| 풍선 2 m (B-01, B-02) | 69–98% / ~4 m | 91–98% / ~4 m |
| 2 m급 고정익 drone (D-01) | 49–55% / 2–5 m | 64–76% / 4–6 m |
| 0.4 m quadcopter (D-02) | 0% | 0% |
| 조류 0.3 m (K-01) | 0–5% | 0–4% |
| Remote ID drone (R-01) | 98% / ~3 m | 98% / ~3 m |
| False tracks | 0–0.1 / step | 0 / step |

Findings

- 소형 quadcopter 추적 불가. 0.4 m 물체는 4K·HFOV 60°에서 약 110 m 이내에서만 안정적으로 관측(4 px 기준 최대 약 330 m)되어 두 node 동시 관측이 어려움.
- 전천 커버리지에 다수 camera 필요. HFOV 60°로 고각 −12°~55°를 덮으려면 dome당 8대 필요. 25 g dome 탑재 가능 여부는 sensor 팀 확인 필요.
- Dome 흔들림 영향은 제한적. IMU 자세 보정으로 흔들림 대부분 상쇄. 잔여 영향은 motion blur(노출 1/500 s 가정)와 time sync 오차. 안정도 0.97 → 0.09에서 고정익 drone 추적률 75% → 64%(700 m 간격). 단, IMU 정확도(0.5°)와 노출 시간 가정에 의존.
- 삼각측량이 성립하는 표적의 위치 정확도는 수 m 수준.

### 6.3 Identification & Threat

Spacing 250 m 기준.

| Target | Identification (추적 구간) | Threat level | Note |
|---|---|---|---|
| 풍선 B-01, B-02 | 풍선 100% | LOW–MEDIUM | 낙하 예상 지점 인구에 따라 변동 |
| 2 m급 고정익 D-01 | Drone 100% | 최고 CRITICAL (86) | 정부청사 도달 75 s 전 최초 HIGH |
| 허가 drone R-01 | Drone 100% | LOW 100% | Remote ID + 허가 목록 |
| 조류 K-01 | Drone으로 판정 | LOW | §5.5의 설계상 가정. 경보 미발생 |

- class-agnostic 검출기 적용 후 고정익 drone은 판정 구간에서 100% drone, 최초 경보 27 s(영상 분류 사용 시 28.5 s).
- 신규 track의 불안정한 속도로 인한 오경보(풍선이 탐지 1 s 만에 HIGH)는 §5.6 initialization guard로 제거.

### 6.4 Detector Synthetic Benchmark

합성 frame 8장 기준.

| Condition | Contrast ≥ 20 | Contrast 10 (faint) | False alarms / frame | Latency |
|---|---|---|---|---|
| 4K, noise 2 | 2–40 px 전부 100% | 2 px 0%, 3 px 50%, ≥ 4 px 100% | 0.12 | 0.21 s |
| 4K, noise 4 | 2–40 px 전부 100% | 2 px 0%, 4 px 75% | 0.25 | 0.24 s |
| HD, noise 2 | 12 px 50%(구름 앞), 그 외 100% | 부분 검출 | 2.1 | 0.05 s |

### 6.5 Decision Support Integration

| Item | Result |
|---|---|
| Response card | `rag/generation/recommend.py`가 위협 단계, 유사 사례, 법적 제약, 권고 수위를 card로 반환 |
| Decision log | `ops/service/decisions.py`가 결정 시각, 선택, 사유, 당시 위협도·card를 JSONL로 저장 |
| UI | 로컬 server와 prototype에서 card 조회·결정 기록 흐름 동작 |
| Tests | `tests/ops/`, `tests/rag/`에서 pipeline·card·결정 기록 검증 |

RAG는 template mode로 고정 규칙과 원문 근거만 제시하며, LLM은 권고 수위 결정에 관여하지 않음.

### 6.6 Planned Comparisons

- 자세 안정도별 탐지율·위치 오차 → ① 단계 무게추 자세 제어가 탐지 성능에 미치는 영향
- 식별 근거 조합별 정확도(영상만 / 바람만 / 결합)

모든 수치는 가상 검출 model 기반. 실제 camera와 검출기로 재측정 필요.

---

## 7. Design Decisions

시연 목적 대비 과도한 요소는 단순화. 마지막 열 조건 발생 시 재도입.

| Initial design | Adopted | Rationale | Revisit when |
|---|---|---|---|
| IMM(운동 model 3종 혼합) | 단일 constant-velocity Kalman filter | 식별은 영상 + 바람 대비 속도로 충분 | 급기동 drone 추적 단절 빈발 시 |
| EKF 내 bearing-only 측정 직접 처리 | Triangulation 후 Kalman filter | 구현·디버깅 용이, 단계별 검증 가능 | 단일 node 관측 상황이 많아 bearing-only tracking 필요 시 |
| Hungarian + JPDA | Nearest-first 배정(gate 99.9%) + 2점 속도 초기화 | 시연 표적 수 적음. 교차 시험 50회 중 ID swap 1회 | 다수 풍선 scenario에서 ID swap 빈발 시 |
| SPRT + GBDT + calibration | 근거별 평균 + 규칙 | 실측 data 없이는 calibration 의미 약함 | 실측 비행·영상 data 축적 시 |
| Monte Carlo 침입 확률·낙하 타원 | 직선 운동 CPA·TTI, 바람 × 낙하 시간 + 원 | 시연 수준에서 차이 미미 | — |
| GOSPA, ECE, Kendall τ 등 | 탐지율, 위치 오차, 분류 정확도, 1순위 적중 | 설명 용이한 지표 우선 | 논문·보고서 수준 평가 필요 시 |
| 오프라인 지도 타일 server | 정적 배경 지도 | 시연 지역 1곳으로 충분 | 지역 변경 필요 시 |
| 딥러닝 검출기 학습 | 학습 없는 `SkyBlobDetector` | 결심지원이 핵심, 학습 data 부재 | 실영상 평가에서 검출률 부족 시 `TorchvisionDetector` 자리에 교체 |

---

## 8. Limitations

- 소형 quadcopter(0.4 m) 미탐지. 해결 방향: 화각 축소(camera 수 증가), node 간격 100–150 m로 축소, 타 sensor 결합.
- 저대비 2–3 px 표적 누락. 실제 거리에서의 대비는 실영상으로만 확인 가능해 scenario 검출 model(4–12 px)은 보수적으로 유지.
- 구름 인접·밀집 표적. 작은 구름 바로 앞 표적, 약 130 px 이내로 밀집한 표적군(풍선 무리)은 배경 추정 교란으로 누락 가능.
- Drone/조류 미구분. 영상·운동 모두 구분 근거 부족(§5.5).
- 합성 평가 범위. 안개, 압축 artifact, 움직이는 구름은 미포함.
- track 단절. 소형·고정익 drone 추적 유지율 약 50%. 결정 대기열은 UI 단 연결로 보완 중(§5.8).

---

## 9. Open Issues

- Camera model·화각·해상도, 탑재 중량: Sensor 팀 확인 필요. 탐지 거리, 방향 정확도, dome 안정성에 영향.
- 영상 전송 방식과 통신 대역: Sensor 팀과 ops가 전체 영상/압축 frame 전송 방식을 정해야 함. 검출 주기와 지연에 영향.
- Time sync: Sensor 팀 확인 필요. 영상·IMU·node 간 시각 정합은 방향 변환과 삼각측량 정확도에 직접 영향.
- Camera calibration: Sensor 팀과 ops가 intrinsics와 장착 각도를 보정해야 함. 방향 변환 정확도에 영향.
- 검증용 실영상: 공개 drone·풍선 영상과 팀 촬영 영상 확보 필요. 실제 검출률과 오경보 확인에 사용.
- Node 배치 간격: 팀 검토 필요. 시야 중첩 여부와 위치 계산 가능 영역을 결정.
- 시연 지역과 참조 data: 보호시설 목록·중요도, 인구 data 출처 확정 필요. 위협도 계산에 영향.
- 허가 비행 목록 출처: 팀 확인 필요. 허가 drone 판별 기준이 됨.
- 위협도 단계 경계값: 팀 검토 필요. 경보 기준을 결정.

Next steps for phase 4: 검증 영상 확보(공개 영상 + 팀 촬영) → 실영상 기반 검출기 평가·튜닝 → 기기 팀 dome camera 영상 검증 → Remote ID 수신기 원본 메시지·RSSI·수신 시각 연동 → 실측 탐지율·지연·위치 오차·오경보율 측정.

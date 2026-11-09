# ops — Ground Station Detection, Tracking & Threat Assessment

정의서 ①–⑥·⑧ 단계 담당. Dome node의 camera 영상·Remote ID·자세 정보를 입력으로 탐지 → 추적 → 식별 → 위협도 평가를 수행하고, 대응 추천(rag)과 운용자 결정을 하나의 화면으로 연결함.

- Design: [docs/DESIGN.md](docs/DESIGN.md)
- Response recommendation: [rag/README.md](../rag/README.md)
- UI prototype: [prototypes/c-uas-ops.html](../prototypes/c-uas-ops.html)

## Overview

운용 화면은 세 흐름으로 나뉨.

- 1. 기기 성능: ① Node status. Dome 안정도·관측 범위·바람 추정을 `nodes/`에서 처리.
- 2. 표적 판단: ② Detection → ③ Localization → ④ Tracking → ⑤ Identification → ⑥ Threat. `perception/`, `localization/`, `tracking/`, `assessment/`가 순서대로 담당.
- 3. 대응 결심: ⑦ Recommendation → ⑧ Decision. 대응 근거는 `rag/`, 결정 기록은 `service/`가 담당.

- 위협도 계산은 고정 규칙 기반의 deterministic 처리. LLM은 판단에 관여하지 않음.
- 경보 경로와 RAG card 생성 경로 분리. Card 생성 지연이 경보 지연으로 이어지지 않음.
- 최종 결정은 운용자 몫. System은 선택지와 근거만 제시함.

## Quick Start

Live server (권장)

```sh
python -m ops.service.server        # --host 127.0.0.1 --port 8090 --speed 2 --spacing 250 --quality 0.95 --seed 0
# http://localhost:8090/
```

- Scenario를 실시간 계산해 WebSocket으로 화면에 전송. 운용자 결정은 `outputs/ops/decisions.jsonl`에 기록.
- 같은 네트워크의 다른 기기에서 접속할 때는 `--host 0.0.0.0`.

Offline replay (server 없이)

```sh
python -m ops.service.export --out prototypes/data/replay.js
open prototypes/c-uas-ops.html      # 가상 애니메이션: ?mode=sim
```

`replay.js`가 있으면 pipeline 결과(node·궤적·식별·위협도·방향선)와 rag 대응 card(유사 사례·조문 인용·권고 수위)를 재생함.

Video detection (② 단독 실행)

```sh
python -m ops.perception.run_video video.mp4 --out detections.jsonl   # 기본: SkyBlobDetector (OpenCV, CPU)
python -m ops.perception.synth_eval                                   # 합성 하늘에서 크기·대비별 검출률
python -m ops.perception.evaluate <image_dir> <label_dir>             # YOLO 형식 라벨 기준 평가
```

- 기본 검출기는 학습·GPU 불필요. OpenCV(`opencv-python-headless`)는 dev 의존성에 포함.
- 딥러닝 검출기는 `--detector torchvision`으로 선택 가능(torch 별도 설치).
- 검출은 "무언가 있음"까지만 담당하고, 종류 판단은 ⑤ Identification이 담당. 결과와 한계는 [DESIGN.md §6.4](docs/DESIGN.md#64-detector-synthetic-benchmark).

## Repository Layout

| Path | Responsibility | Key files |
|---|---|---|
| `core/` | 공통 data schema, 좌표 변환, 참조 정보 형식 | `schemas.py`, `geo.py`, `reference.py` |
| `sources/` | 입력 소스: 시연 scenario, Remote ID decoder | `scenario.py`, `remote_id.py` |
| `nodes/` | ① dome 안정도·관측 범위 평가, 바람 추정 | `status.py`, `wind.py` |
| `perception/` | ② 하늘 영역 객체 검출, pixel → 방위·고각 변환 | `detector.py`, `bearing.py` |
| `localization/` | ③ 다중 node 방향선 교차(triangulation) | `triangulate.py` |
| `tracking/` | ④ Kalman filter, data association, track 관리, Remote ID 융합 | `kalman.py`, `association.py`, `manager.py`, `fusion.py` |
| `assessment/` | ⑤ 식별, ⑥ 위협도, 풍선 낙하 예측 | `classify.py`, `threat.py`, `footprint.py` |
| `service/` | Pipeline 구동, ⑧ 결정 기록, 로컬 server·API | `pipeline.py`, `session.py`, `decisions.py`, `server.py`, `api.py` |

Test: `tests/ops/`

## API

로컬 server(`service/server.py`) 기준. 모든 경로의 prefix는 `/api/ops`.

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | 상태 확인 |
| `GET` | `/meta` | Scenario 메타data(node 배치, 보호구역 등) |
| `GET` | `/state` | 실행 상태와 최신 frame |
| `POST` | `/control` | `pause` · `resume` · `speed` · `restart` · `mode`(`sim` / `live`) |
| `WS` | `/ws` | Frame stream(node·궤적·위협도·대응 card) |
| `POST` | `/ingest` | live mode 장비 입력: node 상태, camera 검출, 바람 |
| `POST` | `/ingest/remote-id` | Dome MCU가 전달한 Remote ID 원본 frame. Decoding은 server에서 수행(ASTM F3411 / Open Drone ID) |
| `POST` | `/decision` | 운용자 결정 기록. 위협도·card는 client 값이 아닌 server snapshot 기준으로 저장 |
| `GET` | `/decisions` | 결정 기록 목록과 요약 |

- live mode 전환: `POST /control {"action":"mode","value":"live"}` 후 `/ingest`로 입력 전송.
- Remote ID decoder 단독 시험: `python -m ops.sources.remote_id`. 공식 레퍼런스 구현 출력과 대조 검증 완료.

## Status

| Phase | Scope | Status |
|---|---|---|
| 1 | 가상 입력, triangulation, tracking, Remote ID 융합 | Done |
| 2 | 식별, 위협도, 풍선 낙하 예측 | Done |
| 3 | rag card 연동, 결정 기록 | Done |
| 4 | 실장비 연결: camera 영상 검출, Remote ID 수신 | In progress |

- 4단계는 software 준비 완료 상태. 입력 경로(`/ingest`, `/ingest/remote-id`)와 검출기 구현 완료, 실장비 연결은 기기 팀 정보·장비 확보 후 진행.
- 기존 앱(`dashboard.py`)과는 아직 미연동.
- 단계별 검증 결과는 [DESIGN.md §6](docs/DESIGN.md#6-evaluation).

## Scope

ops 범위 밖 항목:

- 무게추 자세 제어: 기존 코드(`hanging.py`, Arena)
- Remote ID 수신, camera 촬영: dome firmware(sensor 팀)

# ops: 지상국 분석·결심지원

정의서 결과물 ③. 돔 노드가 보낸 카메라 영상·Remote ID·자세 정보로 표적을 **탐지 → 추적 → 식별 → 위협도 평가**하고, 대응 추천(rag)과 운용자 결정을 화면에서 연결합니다.

설계: [docs/DESIGN.md](docs/DESIGN.md) · 대응 추천: [rag/README.md](../rag/README.md) · 화면 프로토타입: [prototypes/c-uas-ops.html](../prototypes/c-uas-ops.html)

## 처리 흐름

| 화면 | 단계 | 폴더 |
|---|---|---|
| 1. 기기 성능 | ① 돔이 보기 | `nodes/` |
| 2. 표적 판단 | ② 찾기 → ③ 위치 계산 → ④ 추적 → ⑤ 식별 → ⑥ 위협도 | `perception/` → `localization/` → `tracking/` → `assessment/` |
| 3. 대응 결심 | ⑦ 대응 추천 → ⑧ 결심 | `rag/` → `service/` |

## 폴더

| 폴더 | 담당 | 주요 파일 |
|---|---|---|
| `core/` | 모든 단계가 쓰는 데이터 형식, 좌표 변환 | `schemas.py`, `geo.py` |
| `sources/` | 가상 입력: 시연 시나리오 | `scenario.py` |
| `nodes/` | ① 돔 상태 평가(안정도·관측 범위), 바람 | `status.py`, `wind.py` |
| `perception/` | ② 영상 객체 검출, 픽셀 → 방향 변환 | `detector.py`, `bearing.py` |
| `localization/` | ③ 여러 돔의 방향선 교차(삼각측량) | `triangulate.py` |
| `tracking/` | ④ 칼만 필터, 측정–궤적 연결, 궤적 관리, Remote ID 융합 | `kalman.py`, `association.py`, `manager.py`, `fusion.py` |
| `assessment/` | ⑤ 식별, ⑥ 위협도, 풍선 낙하 예측 | `classify.py`, `threat.py`, `footprint.py` |
| `service/` | 단계 연결, ⑧ 결정 기록, API | `pipeline.py`, `decisions.py`, `api.py` |
| `docs/` | 기술 설계 | `DESIGN.md` |

ops 밖에서 담당하는 것:
- 무게추 자세 제어: 기존 코드 (`hanging.py`, Arena)
- Remote ID 수신, 카메라 촬영: 돔 펌웨어 (센서 팀)

관련 위치: 화면 프로토타입 `prototypes/c-uas-ops.html`, 테스트 `tests/ops/`

## 화면에서 결과 보기

**실시간 (로컬 서버, 권장)**

```sh
python -m ops.service.server            # --port 8090 --speed 2 --spacing 250 --quality 0.95 --seed 0
# 브라우저에서 http://localhost:8090/
```

- 서버가 시나리오를 계속 계산해 화면에 WebSocket으로 보내고, 결정은 `outputs/ops/decisions.jsonl`에 바로 저장합니다.
- 장비 입력(4차): `POST /api/ops/control {"action":"mode","value":"live"}`로 바꾼 뒤 `POST /api/ops/ingest`로 돔 상태·카메라 검출을 보냅니다.
- Remote ID: 돔 MCU는 받은 원본 신호만 `POST /api/ops/ingest/remote-id`로 넘기고(바이트·신호 세기·송신 주소·수신 시각), 해석은 서버가 합니다(`sources/remote_id.py`, ASTM F3411 / Open Drone ID, 공식 레퍼런스 구현 결과와 대조 시험). 장비 없이 시험: `python -m ops.sources.remote_id`
- 같은 네트워크의 다른 사람이 접속하려면 `--host 0.0.0.0`.

**서버 없이 (미리 계산한 파일 재생)**

```sh
python -m ops.service.export --out prototypes/data/replay.js
open prototypes/c-uas-ops.html                                   # 가상 애니메이션은 ?mode=sim
```

`prototypes/data/replay.js`가 있으면 프로토타입이 파이프라인 계산 결과(노드·궤적·식별·위협도·방향선)와 rag 대응 카드(유사 사례·조문 인용·권고 수위)를 재생합니다.

## 영상 검출 (② 찾기)

```sh
python -m ops.perception.run_video 영상.mp4 --out detections.jsonl       # 기본: 가벼운 하늘 대비 검출기 (OpenCV, CPU)
python -m ops.perception.synth_eval                                      # 합성 하늘로 크기·대비별 검출률 측정
python -m ops.perception.evaluate 이미지폴더 라벨폴더                       # YOLO 형식 정답으로 측정
```

검출은 "무언가 있다"만 알리고, 종류는 ⑤ 식별이 판단합니다. 학습·GPU가 필요 없습니다. OpenCV가 필요하며(프로젝트 의존성 미포함), 딥러닝 모델은 `--detector torchvision`으로 선택할 수 있습니다(torch 필요). 결과와 한계: [docs/DESIGN.md](docs/DESIGN.md) §5.2.

## 진행 상태

| 단계 | 내용 | 상태 | 산출물 |
|---|---|---|---|
| 1차 | 가상 입력 + 삼각측량 + 추적 + Remote ID 융합 | **완료** | [docs/DESIGN.md](docs/DESIGN.md) §8.1 |
| 2차 | 식별 + 위협도 + 풍선 낙하 예측 | **완료** | [docs/DESIGN.md](docs/DESIGN.md) §8.2 |
| 3차 | rag 카드 연동, 결정·기록 | **완료** | `rag/generation/recommend.py`, `service/decisions.py` |
| 4차 | 실물 연결: 카메라 영상 검출, Remote ID 수신 | **진행 중**: 소프트웨어 준비 완료, 실제 장비 연결은 기기 팀 정보·장비 필요 | `sources/remote_id.py`, `perception/detector.py`, `service/server.py` (`/api/ops/ingest`, `/api/ops/ingest/remote-id`) |

현재 브랜치는 1~3차까지 시연 가능한 가상/로컬 파이프라인을 완성한 상태입니다. 4차는 실제 카메라 영상과 Remote ID 수신기를 연결하는 단계이며, 아직 장비 입력과 프로젝트 의존성은 확정하지 않았습니다.

현재 동작하는 것: ①~⑧ (`nodes/`, `perception/bearing.py`, `localization/`, `tracking/`, `assessment/`, `sources/scenario.py`, `service/pipeline.py`, `service/decisions.py`, `rag/generation/recommend.py`). 참조 정보(보호구역·인구·허가 목록) 형식은 `core/reference.py`. 영상 검출(`perception/detector.py`)은 실제 학습 모델이 필요해 기본 검출기 틀과 가상 입력으로 검증합니다. 기존 앱(`dashboard.py`)에는 아직 연결하지 않았습니다.

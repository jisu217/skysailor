# rag: 오프라인 대응 추천

정의서 결과물 ④. 현재 상황과 비슷한 **과거 Gray-zone 사례**, 관련 **법령·판례·작전 절차**를 찾아, 대응 수위를 근거와 함께 권고하는 카드를 만듭니다. 인터넷 없이 동작합니다.

설계: [docs/DESIGN.md](docs/DESIGN.md) · 위협도 분석: [ops/README.md](../ops/README.md)

## 대응 카드

| 영역 | 내용 |
|---|---|
| 유사 사례 | 비슷한 과거 상황, 그때 취한 조치와 결과 |
| 제약 | 법적·작전적으로 허용·제한되는 것 (원문 인용) |
| 권고 | 대응 수위 하나 + "위협 단계 → 제약 → 사례" 순서의 근거 |

권고 수위는 고정 단계표와 규칙으로 정합니다. LLM은 수위를 정하지 않습니다.

## 처리 흐름

```
[미리 준비]  corpus ──▶ indexing ──▶ 색인
[실행 시]    상황 ──▶ escalation(허용 범위) ──▶ cases(유사 사례) + retrieval(제약 근거)
                 ──▶ generation(권고 수위 + 카드 + 인용 확인) ──▶ ops 화면
```

## 폴더

| 폴더 | 담당 | 주요 파일 |
|---|---|---|
| `corpus/` | 원문: 국가별 사례·법령·판례·절차 | `kr/`, `us/`, `README.md` (형식) |
| `cases/` | 사례 기록 형식, 유사 사례 찾기 | `schema.py`, `match.py` |
| `indexing/` | 법령·판례·절차 쪼개기, 형태소 분석, 색인 생성 | `chunking.py`, `tokenizer.py`, `index.py`, `ingest.py` |
| `retrieval/` | 상황 → 질의, 키워드 + 의미 검색 | `query.py`, `retrieve.py` |
| `generation/` | 대응 수위 단계표, 카드 생성, 인용 확인 | `escalation.py`, `recommend.py`, `verify.py` |
| `eval/` | 평가 시나리오와 지표 | `qrels.example.jsonl`, `evaluate.py` |
| `docs/` | 기술 설계 | `DESIGN.md` |

관련 위치: 테스트 `tests/rag/`

## 실행

```sh
# 의존성(Kiwi, 임베딩 모델)은 구현 시작 시 pyproject.toml에 추가 예정
uv run python -m rag.indexing.fetch_laws      # 법령 원문 갱신
uv run python -m rag.indexing.ingest          # 색인 통계
uv run python -m rag.eval.evaluate
uv run pytest tests/rag -q
```

## 현재 들어 있는 것

- **사례 24건** (`corpus/kr|us|intl/cases/`): 2014~2025 국내외 공개 보도 기준. 출처 URL과 보도 간 차이(`notes`) 포함
- **평가 시나리오 20개** (`eval/qrels.jsonl`, 초안 · 팀 검토 필요): `python -m rag.eval.evaluate --verbose`
- **법령 10개** (`corpus/kr/laws/`): 전파법, 항공안전법, 드론법, 통합방위법, 테러방지법, 군사기지법, 공항시설법, 경찰관 직무집행법, 대통령경호법, 원자력시설방호법. 갱신: `python -m rag.indexing.fetch_laws`
- **카드 생성** (`generation/recommend.py`): 단계표 → 작전 제약 → 법적 근거(조문 원문 인용, 원문 대조) → 유사 사례 → 권고 수위. 템플릿 모드
- 판례·작전 절차 문서는 아직 없음. 의미 검색(bge-m3)과 Kiwi는 설치되면 자동으로 사용

## 구현 상태

| 항목 | 상태 |
|---|---|
| 사례 기록 및 유사 사례 검색 | 완료 |
| 법령 corpus | 초안 완료 |
| 대응 수위 단계표 | 완료 |
| 대응 카드 생성 | 완료, 템플릿 모드 |
| ops 연동 | 완료 |
| 평가 시나리오 | 초안, 팀 검토 필요 |
| 판례·작전 절차 문서 | 미작성 |
| 의미 검색, Kiwi 형태소 분석 | 의존성 추가 전 |

전체 프로젝트의 1차~4차 진행 상태는 [ops/README.md](../ops/README.md)에 대표로 정리합니다. 이 문서는 rag 모듈의 사용법과 구현 상태만 다룹니다.

# rag — Offline Response Recommendation

정의서 ⑦ 대응 추천 단계 담당. 현재 상황과 유사한 과거 Gray-zone 사례와 관련 법령·판례·작전 절차를 검색해, 대응 수위를 근거와 함께 권고하는 card를 생성함. 인터넷 연결 없이 동작.

- Design: [docs/DESIGN.md](docs/DESIGN.md)
- Threat assessment: [ops/README.md](../ops/README.md)

## Overview

대응 card는 세 영역으로 구성됨.

- Similar cases: 유사 과거 상황, 당시 조치와 결과.
- Constraints: 법적·작전적 허용·제한 사항. 원문 인용을 함께 표시.
- Recommendation: 대응 수위 1개와 "위협 단계 → 제약 → 사례" 순서의 근거.

- 권고 수위는 고정 단계표와 규칙으로 결정. LLM은 수위 결정에 관여하지 않음.
- 같은 상황이면 같은 card 생성(deterministic).

```
[offline]  corpus ──▶ indexing ──▶ index
[runtime]  situation ──▶ escalation (허용 범위) ──▶ cases (유사 사례) + retrieval (제약 근거)
                     ──▶ generation (권고 수위 + card + 인용 검증) ──▶ ops UI
```

## Quick Start

```sh
uv run python -m rag.indexing.fetch_laws      # 법령 원문 갱신 (국가법령정보센터 Open API)
uv run python -m rag.indexing.ingest          # chunk·token 통계
uv run python -m rag.eval.evaluate --verbose  # 평가 시나리오 실행
uv run pytest tests/rag -q
```

Optional dependencies(미설치 시 자동 fallback):

| Package | Role | Fallback |
|---|---|---|
| `kiwipiepy` | 한국어 형태소 분석(BM25 tokenization) | 어절 + 한글 bigram |
| `sentence-transformers` + `BAAI/bge-m3` | Dense retrieval(`ingest --dense BAAI/bge-m3`) | BM25 단독 |

## Repository Layout

| Path | Responsibility | Key files |
|---|---|---|
| `corpus/` | 원문: 국가별 사례·법령·판례·절차 | `kr/`, `us/`, `intl/`, [README.md](corpus/README.md) |
| `cases/` | 사례 schema, 유사 사례 매칭 | `schema.py`, `match.py` |
| `indexing/` | 법령 수집, chunking, tokenization, hybrid index | `fetch_laws.py`, `chunking.py`, `tokenizer.py`, `index.py`, `ingest.py` |
| `retrieval/` | 상황 → 질의 생성, BM25 + dense + RRF | `query.py`, `retrieve.py` |
| `generation/` | 대응 수위 단계표, card 생성, 인용 검증 | `escalation.py`, `recommend.py`, `verify.py` |
| `eval/` | 평가 scenario와 지표 | `qrels.jsonl`, `evaluate.py` |

Test: `tests/rag/`

## Corpus

| Type | Count | Location |
|---|---|---|
| Cases | 24건(국내 11, 미국 5, 기타 해외 8), 2014–2025 공개 보도 기준 | `corpus/{kr,us,intl}/cases/` |
| Laws | 10개: 전파법, 항공안전법, drone법, 통합방위법, 테러방지법, 군사기지법, 공항시설법, 경찰관 직무집행법, 대통령경호법, 원자력시설방호법 | `corpus/kr/laws/` |
| Precedents · Procedures | 미작성 | `corpus/*/precedents/`, `corpus/*/procedures/` |
| Eval scenarios | 20개(초안, 팀 검토 필요) | `eval/qrels.jsonl` |

- 사례마다 출처 URL과 보도 간 차이(`notes`) 기록.
- 평가 정답은 초안 정책과의 일치도 측정용이며 ground truth 아님.

## Status

- 사례 schema와 유사 사례 매칭: Done
- 법령 corpus: Draft
- 대응 수위 단계표: Done
- 대응 card 생성: Done (template mode)
- ops 연동: Done
- 평가 scenario: Draft, 팀 검토 필요
- 판례·작전 절차 문서: Not started
- Kiwi, dense retrieval: Optional, project 의존성 미포함

Project 전체 단계별 상태는 [ops/README.md](../ops/README.md#status) 참고.

# rag Technical Design

Scope: 정의서 ⑦ 대응 추천 단계. 위협도까지의 분석은 [ops/docs/DESIGN.md](../../ops/docs/DESIGN.md) 참고.
사용법과 현재 상태는 [rag/README.md](../README.md) 참고.

## 목차

1. [Problem Statement](#1-problem-statement)
2. [Design Principles](#2-design-principles)
3. [Retrieval](#3-retrieval)
4. [Escalation Policy](#4-escalation-policy-raggenerationescalationpy)
5. [Response Card](#5-response-card-raggeneration)
6. [Evaluation](#6-evaluation)
7. [Models & Runtime](#7-models--runtime)
8. [Design Decisions](#8-design-decisions)
9. [Risks & Open Issues](#9-risks--open-issues)

---

## 1. Problem Statement

정의서의 대응 추천 요구:

현재 침해 상황과 유사한 기존 Gray-zone 사례, 관련 법규, 판례, 작전 절차를 검색해 대응 판단의 근거를 제공한다. 현장 지휘관은 단순히 "위험하다"는 경보가 아니라, 과거 유사 상황에서 어떤 조치가 이루어졌고 어떤 법적·작전적 제약이 있었는지 함께 확인할 수 있다. RAG는 대응 수위를 정당화하고, 과잉 대응이나 대응 지연을 줄이며, 사람이 더 빠르고 일관된 결정을 내리도록 돕는다.

대응 card가 답해야 할 운용자의 세 가지 질문:

- 유사 상황이 과거에 있었나? 당시 조치와 결과는? Similar cases 영역에서 사례 기록을 제시.
- 무엇이 허용되고 무엇이 제한되나? Constraints 영역에서 법령, 판례, 작전 절차를 제시.
- 어느 수위로 대응해야 하나? Recommendation + rationale 영역에서 단계표와 위 두 영역의 근거를 연결.

---

## 2. Design Principles

- Case-first: 법령 조문보다 "과거 실제 대응"을 우선 제시.
- No judgment: 위협도는 ops가 결정. RAG는 근거 검색과 수위 정당화만 담당.
- Bounded: 위협 단계별 허용 범위는 고정 표로 결정. RAG는 범위 내 선택·축소만 가능.
- Conservative default: 근거 부족 시 권고는 "관측 지속".
- Deterministic: 같은 상황이면 같은 card.
- Fully offline: 모든 자료와 model을 로컬 보관.
- Country-swappable: `corpus/kr`, `corpus/us` 교체만으로 국외 mode 전환.

---

## 3. Retrieval

### 3.1 Case Matching (`rag/cases/`)

Schema. 사례를 text chunk가 아닌 정형 record로 관리(`rag/cases/schema.py`, file 1개당 사례 1건).

| Field | Example |
|---|---|
| 일시, 지역, 시설 유형 | 2024-06, 서울·경기, 수도권 |
| 표적 유형, 수량, Remote ID | 풍선, 약 600개, 없음 |
| 조치(순서대로) | 관측 → 관계기관 통보 → 낙하 후 수거 |
| 최고 대응 수위 | 통보 |
| 결과, 부수 피해 | 재산 피해 발생 … |
| 적용 제약 | 인구 밀집 지역 격추 시 낙하물 피해 우려 |
| 출처 | 공개 보도·공식 발표 URL |

Matching. 현재 상황과 사례 항목 간 가중 일치 점수. 동점 시 최신 사례 우선.

```
similarity = 3·[target class] + 2·[zone type] + 1·[population density] + 1·[Remote ID]
```

- 상위 3건 제시, 일치 항목(`matched_on`) 함께 표시.
- 공개 사례 규모가 수십 건 수준이라 vector search 대비 정확도·설명 가능성 모두 우위.

### 3.2 Document Chunking (`rag/indexing/`)

| Type | Example | Chunk unit |
|---|---|---|
| Law | 항공안전법, drone법, 전파법, 통합방위법 | 조·항(검색은 항 단위, 표시는 조 전체) |
| Precedent | 관련 판결 | 문단 |
| Procedure | 공개 대응 지침·manual | 문단 |

- chunk마다 법령명, 조문, 문서 유형, 국가, 시행일, 출처 metadata 부여.
- 한국어 tokenization은 Kiwi 형태소 분석. 미적용 시 "무인비행장치를"과 "무인비행장치"가 별개 token으로 처리되는 문제. Kiwi 미설치 환경은 어절 + 한글 bigram으로 fallback. "제29조" 형태 조문 참조는 단일 token 유지.

### 3.3 Hybrid Search (`rag/retrieval/`)

```
situation → 허용 범위 내 대응 수위별 query 생성
          → 국가·문서 유형 metadata filter
          → BM25 top 30  (+ dense bge-m3 top 30, 활성화 시)
          → Reciprocal Rank Fusion (k = 60)
          → 조 단위 중복 제거 → top 5
```

- query는 사용자 입력이 아닌 상황에서 자동 생성. 예: 전파 차단 → "전파 차단 장치 사용 요건 무인비행장치".
- 같은 상황이면 같은 query, 같은 결과.

---

## 4. Escalation Policy (`rag/generation/escalation.py`)

정의서의 "대응 수위 정당화"와 "과잉·지연 감소"를 구현하는 핵심 장치.

```
관측 지속 → 관계기관 통보 → 경보 발령 → 전파 차단 → 물리적 무력화
 observe      report          alert        rf_jam       kinetic
```

Allowed range by threat level (초기값, 팀 검토로 확정)

| Threat level | Allowed range |
|---|---|
| LOW | observe |
| MEDIUM | observe – report |
| HIGH | observe – alert |
| CRITICAL | observe – kinetic |

Recommendation rules

1. 위협 단계로 허용 범위 결정(고정 표).
2. 제약에 해당하는 수위 제외. 예: 인구 밀집 지역 → kinetic 제외, 전파 차단 권한 요건 미충족 → rf_jam 제외.
3. 잔여 범위 내에서 유사 사례의 실제 최고 대응 수위 권고. 사례 부재 시 잔여 범위의 최저 수위.
4. 근거(사례·조문) 전무 시 "관측 지속" 권고 + "근거 부족" 표시.

권고는 항상 "위협 단계 → 제약 → 사례" 순서로 설명 가능. 허용 범위를 넘는 권고(과잉 대응)는 구조적으로 불가.

---

## 5. Response Card (`rag/generation/`)

### 5.1 Layout

```
┌ T-07 · 신원 미상 드론 · 위협 HIGH ─────────────────────────────┐
│ [유사 사례]                                                     │
│  · 2022.12 무인기 영공 침범 (표적·시설 유형 일치)               │
│    조치: 관측 → 경보 → 추적 … / 결과: …                         │
│  · …                                                            │
│ [제약]                                                          │
│  · 법적: ○○법 제○조 — "…" (원문 인용)                          │
│  · 작전: 인구 밀집 지역 → 무력화 시 낙하 피해                   │
│ [권고]  경보 발령   (허용 범위: 관측~경보)                      │
│  근거: 위협 HIGH → 범위 관측~경보 → 유사 사례 2건이 경보까지 대응 │
│ ※ AI는 선택지와 근거만 제시합니다. 최종 결정은 운용자가 합니다.  │
└─────────────────────────────────────────────────────────────────┘
```

출력 schema: `ops/core/schemas.py`의 `Recommendation`.

### 5.2 Generation Modes

- Template mode (default): 고정 문장 틀에 사례·조문·규칙 결과를 채움. hallucination 여지 없음, 즉시 응답.
- LLM mode (optional, 미구현): 로컬 LLM이 동일 근거로 "근거" 문장만 재작성. 권고 수위는 §4 규칙으로 고정되며 LLM이 변경 불가.

### 5.3 Citation Verification (`rag/generation/verify.py`)

Card에 인용한 문장의 원문 존재 여부를 문자열 대조로 검증(공백·문장부호 정규화). 검증 실패 인용은 card에서 제거.

---

## 6. Evaluation

### 6.1 Scenarios (`rag/eval/qrels.jsonl`)

Scenario 20개. 각 scenario에 팀이 정한 정답 부여:

- 적정 대응 수위(및 허용 가능 범위)
- 제시되어야 할 사례
- 근거 조문

근거가 없어야 정답인 scenario 일부 포함. 정답은 초안 정책과의 일치도 측정용이며 ground truth 아님.

### 6.2 Metrics (`rag/eval/evaluate.py`)

| Claim (정의서) | Metric | Method |
|---|---|---|
| 유사 사례 제시 | Case hit@3 | 정답 사례가 제시된 3건 내 포함되는 비율 |
| 법적 근거 제시 | Article recall | 정답 조문이 인용에 포함되는 비율(조문 지정 scenario 한정) |
| 과잉·지연 감소 | Exact / within / over / under | 권고 수위를 정답 수위·허용 범위와 비교 |
| 일관된 결정 | Consistency | 동일 상황 2회 실행 시 card 동일 여부 |
| 근거 신뢰성 | Citation pass rate | §5.3 검증 통과 인용 비율 |
| 더 빠른 결정 | Decision time | Card 유무에 따른 소규모 사용자 test(예정) |

Key comparison for presentation: card 유/무 조건에서 운용자 결정의 적정 수위 일치율과 결정 시간. 정의서 주장을 가장 직접적으로 검증하는 지표.

---

## 7. Models & Runtime

공개 model을 로컬에서 실행하며 자체 학습 없음. 기본 동작은 추가 model 없이 BM25 + template mode.

| Component | Required | Candidate | Without it |
|---|---|---|---|
| Morphological analyzer | Optional | `kiwipiepy` | 어절 + 한글 bigram |
| Embedding model | Optional | `BAAI/bge-m3`(다국어·한국어), `sentence-transformers` | BM25 단독 |
| Generative LLM | LLM mode 전용 | Qwen·Gemma·EXAONE 계열 7–9B, Ollama | template mode |

- optional 의존성은 project `pyproject.toml`에 미포함. 도입 시 별도 dependency group으로 추가 예정.
- Model별 상업 이용 조건 상이(예: EXAONE은 비상업 license). LLM 선정 시 license 확인 필수.

---

## 8. Design Decisions

초기 설계 중 시연 목적 대비 과도한 요소는 단순화. 마지막 열 조건 발생 시 재도입.

| Initial design | Adopted | Rationale | Revisit when |
|---|---|---|---|
| 법령 조문 검색 중심 | 사례 중심 + 법령·판례·절차 | 정의서 핵심은 "과거 실제 대응" | — (방향 전환) |
| 대응 선택지별 card 나열 | 3단 card + 단일 권고 수위 | 운용자의 즉시 판독성 | — (방향 전환) |
| 사례 vector search | 항목 일치 점수 | 수십 건 규모에서 정확도·설명 가능성 우위 | 사례 수백 건 이상 |
| Reranker(bge-reranker) | 미적용 | 문서 수 대비 비용 과다 | 조문 recall 저조 시 |
| NLI 기반 인용 검증 | 문자열 대조 | template mode는 원문 그대로 인용 | LLM mode에서 재작성 문장 사용 시 |
| LLM JSON 강제·인용 ID 제한 | LLM은 근거 문장 재작성만 | 수위 결정을 규칙으로 이관해 LLM 역할 축소 | — |
| Index hash versioning | 국가·시행일·chunk 수 기반 version 문자열 | 시연 기간 내 법령 변경 가능성 낮음 | 장기 운영 시 |
| nDCG, MRR, ALCE citation metrics | Hit rate, 과잉·과소 비율, consistency | 정의서 주장과 직결되는 지표 우선 | 검색 성능 논문 수준 비교 필요 시 |
| 검색 구성 6종 비교 실험 | Card 유/무 비교 1종 | 발표 전달력 우선 | 일정 여유 시 |

---

## 9. Risks & Open Issues

- 작전 절차 확보: 대부분 비공개일 수 있음. 공개 manual을 우선 조사하고, 미확보 시 "가상 절차 문서"임을 명시하고 사용.
- 판례: Drone·풍선 관련 국내 판례가 희소할 수 있음. 항공·전파 관련 판례로 범위를 확대하고, 부재 시 판례 영역 축소.
- 사례 품질: 공개 정보만으로는 조치·결과가 불완전할 수 있음. 확인된 항목만 기록하고 출처를 필수로 둠.
- 허용 범위 표: 팀 임의 설정 시 근거가 취약할 수 있음. 사례·법령으로 칸별 근거를 문서화하고, 가능 시 외부 검토.
- 평가 정답: 정답 수위 결정 주체가 불명확할 수 있음. 팀원 2인 이상이 독립 작성한 뒤 불일치를 기록.
- 국외 mode: 대상 국가·문서가 아직 미정. 한국 mode 완성 후 결정.

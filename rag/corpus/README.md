# Corpus

RAG가 참조하는 원문 데이터 작성 규칙입니다. 공개 문서만 넣고, 진행 상태나 구현 설명은 [rag/README.md](../README.md)와 [rag/docs/DESIGN.md](../docs/DESIGN.md)에 둡니다.

```
kr/      한국 (사례·법령·판례·절차)
us/      미국 (국외 모드)
intl/    기타 해외 참고 사례
  └─ 각 폴더: cases/  laws/  precedents/  procedures/
```

모드별로 읽는 폴더:
- **한국 모드(kr):** kr + us + intl. 해외 선례도 판단에 참고가 되기 때문입니다.
- **미국 모드(us):** us + intl

## 사례 기록 (`cases/*.json`)

`rag/cases/schema.py`의 `Case` 형식을 따르고, 파일 하나에 사례 하나입니다.

| 필드 | 내용 |
|---|---|
| `target_class`, `count`, `region`, `zone_type`, `population`, `rid` | 상황. 유사 사례 찾기에 쓰임 |
| `actions_taken` | 실제로 취한 조치 (순서대로) |
| `max_action` | 가장 높았던 대응 수위 (observe / report / alert / rf_jam / kinetic) |
| `outcome`, `collateral` | 결과와 부수 피해 |
| `constraints` | 그때 작용한 법적·작전적 제약 |
| `sources` | 출처 URL (필수) |
| `notes` | 보도마다 다른 수치, 확인되지 않은 부분 |

**작성 원칙:** 출처에서 확인된 사실만 씁니다. 보도마다 다르거나 확인되지 않은 내용은 본문에 단정하지 않고 `notes`에 적습니다.

## 문서 원문 (`laws/`, `precedents/`, `procedures/`)

원문 파일마다 같은 이름의 `.meta.json`을 둡니다.

```json
{ "doc": "항공안전법", "doc_type": "law", "country": "kr",
  "effective_date": "YYYY-MM-DD", "source_url": "https://www.law.go.kr/..." }
```

`doc_type`: `law` | `precedent` | `procedure`

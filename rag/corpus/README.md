# Corpus

RAG 참조 원문 data의 작성 규칙. 공개 문서만 수록하며, 진행 상태와 구현 설명은 [rag/README.md](../README.md), [rag/docs/DESIGN.md](../docs/DESIGN.md) 참고.

## Layout

```
kr/      한국 (사례·법령·판례·절차)
us/      미국 (국외 모드)
intl/    기타 해외 참고 사례
  └─ 각 폴더: cases/  laws/  precedents/  procedures/
```

Mode별 참조 folder:

- Korea mode (`kr`): `kr` + `us` + `intl`. 해외 선례도 판단 근거로 활용.
- US mode (`us`): `us` + `intl`

## Case Records (`cases/*.json`)

`rag/cases/schema.py`의 `Case` schema 준수, file 1개당 사례 1건.

기록 필드:

- `target_class`, `count`, `region`, `zone_type`, `population`, `rid`: 상황 정보. 유사 사례 매칭에 사용.
- `actions_taken`: 실제 조치. 순서대로 기록.
- `max_action`: 최고 대응 수위(`observe` / `report` / `alert` / `rf_jam` / `kinetic`).
- `outcome`, `collateral`: 결과와 부수 피해.
- `constraints`: 당시 작용한 법적·작전적 제약.
- `sources`: 출처 URL. 필수.
- `notes`: 보도 간 수치 차이, 미확인 사항.

Authoring rule: 출처로 확인된 사실만 기재. 보도 간 상이하거나 미확인된 내용은 본문에 단정하지 않고 `notes`에 기록.

## Source Documents (`laws/`, `precedents/`, `procedures/`)

원문 file마다 동일 이름의 `.meta.json` 동반.

```json
{ "doc": "항공안전법", "doc_type": "law", "country": "kr",
  "effective_date": "YYYY-MM-DD", "source_url": "https://www.law.go.kr/..." }
```

`doc_type`: `law` | `precedent` | `procedure`

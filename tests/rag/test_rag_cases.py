from rag.cases.match import load, similar


def test_all_case_records_validate():
    cases = load('kr')
    assert len(cases) >= 10
    assert all(c.sources and c.sources[0].startswith('http') for c in cases)
    assert len({c.case_id for c in cases}) == len(cases)


def test_capital_drone_matches_2022_incursion_first():
    top = similar(dict(target_class='drone', zone_type='capital', population='high', rid='none'), load('kr'))
    assert top[0].case_id == 'kr-2022-12-capital-drone'
    assert top[0].similarity == 1.0 and '시설 유형' in top[0].matched_on


def test_airport_balloon_matches_incheon_case_first():
    top = similar(dict(target_class='balloon', zone_type='airport', population='medium', rid='none'), load('kr'))
    assert top[0].case_id == 'kr-2024-06-incheon-balloon'
    assert all('풍선' in r.title for r in top)            # only balloon cases count as similar


def test_us_mode_excludes_korean_cases():
    ids = {c.case_id for c in load('us')}
    assert 'us-2023-02-china-balloon' in ids and not any(i.startswith('kr-') for i in ids)


def test_no_case_for_unmatched_class():
    assert similar(dict(target_class='bird', zone_type='capital', population='high', rid='none'), load('kr')) == []

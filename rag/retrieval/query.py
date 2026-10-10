"""Deterministic situation and queries.

situation() turns a track + threat + zone into the fields cases are matched on; queries()
builds one legal query per action that needs a basis. Same situation → same queries → same
evidence.
"""

ZONE_CONTEXT = {
    'capital': '대통령 경호 안전활동 국가중요시설 군사활동 대테러활동',
    'military': '군사기지 군사시설 국가안전보장 군사활동',
    'airport': '공항시설법 금지행위 위반행위의 제지',
    'power': '원자력시설 물리적방호 국가중요시설',
    'residential': '위험 발생의 방지 범죄의 예방과 제지',
}

ACTION_QUERY = {
    'report': '초경량비행장치 비행승인 비행제한공역 위반 신고',
    'alert': '국가중요시설 경비 보안 방호 위험 발생의 방지 경고',
    'rf_jam': '전파차단장치 드론 공공안전 위협 수단 전파이용 방해 차단 사용',
    'kinetic': '드론 위협 제지 범죄의 예방 위해 방지 무력',
}


# Which statutes may ground each action (keeps e.g. the jamming clause from answering 'alert').
ACTION_DOCS = {
    'report': ('항공안전법', '공항시설법', '드론 활용의 촉진 및 기반조성에 관한 법률'),
    'alert': ('통합방위법', '경찰관 직무집행법', '공항시설법', '군사기지 및 군사시설 보호법',
              '대통령 등의 경호에 관한 법률', '원자력시설 등의 방호 및 방사능 방재 대책법'),
    'rf_jam': ('전파법',),
    'kinetic': ('경찰관 직무집행법', '통합방위법', '국민보호와 공공안전을 위한 테러방지법',
                '군사기지 및 군사시설 보호법', '대통령 등의 경호에 관한 법률'),
}


def level(popv: float) -> str:
    return 'high' if popv >= .6 else 'medium' if popv >= .3 else 'low'


def situation(track, threat, zone, popv: float) -> dict:
    c = track.classes
    cls = max(('drone', 'balloon', 'bird', 'unknown'), key=lambda k: getattr(c, k))
    return dict(target_class=cls, zone_type=getattr(zone, 'kind', None) or 'capital', population=level(popv),
                rid='present' if track.rid is not None else 'none', permitted=bool(track.permitted), level=threat.level)


def queries(situation: dict, actions) -> dict[str, str]:
    ctx = ZONE_CONTEXT.get(situation['zone_type'], '')
    return {a: f'{ACTION_QUERY[a]} {ctx}' for a in actions if a in ACTION_QUERY}

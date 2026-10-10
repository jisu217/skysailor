"""Download statutes from the 국가법령정보센터 open API and write article-structured text.

python -m rag.indexing.fetch_laws [--oc YOUR_KEY] [--out rag/corpus/kr/laws]

Each law becomes <name>.txt (조·항·호 lines, 부칙 excluded) plus <name>.meta.json with the
effective date. OC is the API user key; 'test' works for trials, register your own at
https://open.law.go.kr for regular use.
"""
import argparse
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

LAWS = ['전파법', '항공안전법', '드론 활용의 촉진 및 기반조성에 관한 법률', '통합방위법',
        '국민보호와 공공안전을 위한 테러방지법', '군사기지 및 군사시설 보호법', '공항시설법',
        '경찰관 직무집행법', '대통령 등의 경호에 관한 법률', '원자력시설 등의 방호 및 방사능 방재 대책법']
API = 'https://www.law.go.kr/DRF/lawService.do'


def _t(e):
    return (e.text or '').strip() if e is not None else ''


def fetch(name: str, oc: str) -> bytes:
    q = urllib.parse.urlencode(dict(OC=oc, target='law', type='XML', LM=name))
    with urllib.request.urlopen(f'{API}?{q}', timeout=30) as r:
        return r.read()


def to_text(xml: bytes):
    root = ET.fromstring(xml)
    info = root.find('기본정보')
    lines = []
    for u in root.iter('조문단위'):
        body = _t(u.find('조문내용'))
        if _t(u.find('조문여부')) != '조문':
            if body:
                lines.append('\n'+body)
            continue
        lines.append(body)
        for h in u.findall('항'):
            if _t(h.find('항내용')):
                lines.append(_t(h.find('항내용')))
            for ho in h.findall('호'):
                lines.append('  '+_t(ho.find('호내용')))
                for m in ho.iter('목내용'):
                    lines.append('    '+(m.text or '').strip())
    text = re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip()+'\n'
    d = lambda s: f'{s[:4]}-{s[4:6]}-{s[6:]}'
    meta = dict(doc=_t(info.find('법령명_한글')), doc_type='law', country='kr', effective_date=d(_t(info.find('시행일자'))),
                promulgated=d(_t(info.find('공포일자'))), law_id=_t(info.find('법령ID')),
                source_url=f'https://www.law.go.kr/법령/{_t(info.find("법령명_한글"))}', retrieved=date.today().isoformat(),
                note='국가법령정보센터 공개 API 원문. 부칙 제외')
    return text, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--oc', default='test')
    ap.add_argument('--out', default='rag/corpus/kr/laws')
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for name in LAWS:
        text, meta = to_text(fetch(name, a.oc))
        stem = meta['doc'].replace(' ', '_')
        (out/f'{stem}.txt').write_text(text, encoding='utf-8')
        (out/f'{stem}.meta.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print(f'{meta["doc"]}: 시행 {meta["effective_date"]}, {len(text)/1e3:.0f} kB')


if __name__ == '__main__':
    main()

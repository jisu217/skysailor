"""Structure-aware chunking.

Statutes: split by 조 (article) and 항 (paragraph, ①②…); the 항 is the retrieval unit and the
whole 조 is kept as parent context. 호 (numbered items) stay with their 항.
Precedents / procedures: paragraph chunks (~800 chars).
"""
import re
from dataclasses import dataclass, field

ART = re.compile(r'^(제(\d+)조(?:의(\d+))?)\(([^)]*)\)\s*(.*)$')
DELETED = re.compile(r'^제\d+조(?:의\d+)?\s*삭제')            # '제13조 삭제 <2014.5.20>'
PARA = re.compile(r'^([①-⑳])\s*')
CIRCLED = '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳'


@dataclass
class Chunk:
    chunk_id: str
    text: str
    parent_id: str | None
    meta: dict = field(default_factory=dict)


def _articles(text):
    cur = None
    for line in text.splitlines():
        m = ART.match(line.strip())
        if m:
            if cur:
                yield cur
            cur = dict(ref=m.group(1), title=m.group(4), lines=[m.group(5)] if m.group(5) else [])
        elif DELETED.match(line.strip()):
            if cur:
                yield cur
            cur = None
        elif cur is not None and line.strip():
            if re.match(r'^제\d+(장|절|관)', line.strip()):
                yield cur; cur = None
                continue
            cur['lines'].append(line.rstrip())
    if cur:
        yield cur


def chunk_law(text: str, meta: dict) -> list[Chunk]:
    out = []
    key = meta.get('law_id') or meta['doc']
    for a in _articles(text):
        pid = f'{key}:{a["ref"]}'
        head = f'{meta["doc"]} {a["ref"]}({a["title"]})'
        full = head+'\n'+'\n'.join(a['lines'])
        out.append(Chunk(pid, full, None, dict(meta, article=a['ref'], title=a['title'], level='article')))
        paras, cur = [], None
        for ln in a['lines']:
            m = PARA.match(ln.strip())
            if m:
                cur = [m.group(1), [ln.strip()]]; paras.append(cur)
            elif cur:
                cur[1].append(ln.strip())
        for sym, lines in paras:
            n = CIRCLED.index(sym)+1
            out.append(Chunk(f'{pid}:{n}', head+'\n'+'\n'.join(lines), pid,
                             dict(meta, article=f'{a["ref"]} 제{n}항', title=a['title'], level='paragraph')))
    return out


def chunk_prose(text: str, meta: dict, max_chars: int = 800) -> list[Chunk]:
    out, buf, k = [], '', 0
    key = meta.get('law_id') or meta['doc']
    for para in [p.strip() for p in text.split('\n\n') if p.strip()]:
        if buf and len(buf)+len(para) > max_chars:
            out.append(Chunk(f'{key}:p{k}', buf, None, dict(meta, article=f'문단 {k+1}', level='prose'))); k += 1; buf = ''
        buf = (buf+'\n\n'+para).strip()
    if buf:
        out.append(Chunk(f'{key}:p{k}', buf, None, dict(meta, article=f'문단 {k+1}', level='prose')))
    return out

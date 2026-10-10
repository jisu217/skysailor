"""Korean tokenisation for BM25: Kiwi content morphemes when kiwipiepy is installed, otherwise
whole words plus Hangul character bigrams (handles particles such as 드론을/드론의 reasonably).
Article references like 제29조 stay one token either way."""
import re

ARTICLE = re.compile(r'제\d+조(?:의\d+)?')
WORD = re.compile(r'[가-힣]+|[A-Za-z]+|\d+')

try:                                                        # optional dependency
    from kiwipiepy import Kiwi
    _kiwi = Kiwi()
except Exception:                                           # pragma: no cover - depends on environment
    _kiwi = None

CONTENT = ('NN', 'VV', 'VA', 'SL', 'SN', 'XR')


def tokenize(text: str) -> list[str]:
    arts = ARTICLE.findall(text)
    if _kiwi is not None:
        toks = [t.form for t in _kiwi.tokenize(text) if t.tag.startswith(CONTENT)]
        return arts+toks
    toks = list(arts)
    for w in WORD.findall(text):
        toks.append(w)
        if re.fullmatch(r'[가-힣]{3,}', w):
            toks += [w[i:i+2] for i in range(len(w)-1)]
    return toks


def backend() -> str:
    return 'kiwi' if _kiwi is not None else 'bigram'

"""Citation check: the quoted text must appear in the cited chunk after normalising whitespace
and punctuation. Unverified citations are dropped from the card."""
import re

_N = re.compile(r'[\s·ㆍ.,()「」『』"\'“”‘’<>〈〉\-]+')


def norm(s: str) -> str:
    return _N.sub('', s)


def verify(citation, chunk) -> bool:
    return bool(citation.quote) and chunk is not None and norm(citation.quote) in norm(chunk.text)

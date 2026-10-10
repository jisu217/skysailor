"""Escalation ladder and the default allowed range per threat level.

The range is a fixed, reviewable table. Cases and constraints then justify (or narrow)
the level inside it; RAG never widens the range.
"""

LADDER = ['observe', 'report', 'alert', 'rf_jam', 'kinetic']

# Starting values; to be agreed with the team / domain reviewer.
ALLOWED = {
    'LOW': ['observe'],
    'MEDIUM': ['observe', 'report'],
    'HIGH': ['observe', 'report', 'alert'],
    'CRITICAL': ['observe', 'report', 'alert', 'rf_jam', 'kinetic'],
}


def allowed_range(level: str) -> list[str]:
    return ALLOWED[level]

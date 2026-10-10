"""Case record format. One JSON file per case under rag/corpus/<kr|us|intl>/cases/.

Only publicly reported facts; disagreements between sources go in `notes`.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Case(BaseModel):
    model_config = ConfigDict(extra='forbid')
    case_id: str
    title: str
    date: str = Field(description='YYYY-MM or YYYY-MM-DD')
    country: str = 'kr'
    target_class: Literal['drone', 'balloon', 'bird', 'unknown']
    count: int | None = None
    region: str
    zone_type: Literal['capital', 'military', 'airport', 'power', 'residential']
    population: Literal['low', 'medium', 'high']
    rid: Literal['present', 'none', 'unknown'] = 'unknown'
    actions_taken: list[str] = Field(description='in order, mapped to the escalation ladder where possible')
    max_action: Literal['observe', 'report', 'alert', 'rf_jam', 'kinetic']
    outcome: str
    collateral: str | None = None
    constraints: list[str] = Field(default_factory=list, description='legal / operational limits that applied')
    sources: list[str] = Field(description='public URLs or document references')
    notes: list[str] = Field(default_factory=list, description='where sources disagree or facts are unconfirmed')

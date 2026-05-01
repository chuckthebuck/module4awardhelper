from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Literal


@dataclass
class FourAwardNomination:
    section_title: str
    section_index: int
    raw_text: str
    users: List[str]
    article: str


@dataclass
class FourAwardRecord:
    user: str
    article: str
    award_date: Optional[str]
    creation_date: Optional[str]
    dyk_date: Optional[str]
    ga_date: Optional[str]
    fa_date: Optional[str]
    display_user: Optional[str] = None


@dataclass
class VerificationIssue:
    code: str
    reason: str


Status = Literal["approved", "failed_to_verify", "manual_review_needed"]


@dataclass
class NominationResult:
    nomination: FourAwardNomination
    status: Status
    issues: List[VerificationIssue] = field(default_factory=list)
    record: Optional[FourAwardRecord] = None

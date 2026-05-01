from __future__ import annotations

from typing import List

from .config import ENABLED, MAX_NOMINATIONS_PER_RUN
from .parser import parse_nominations
from .reviewer import review_nomination
from .records import sync_records_table
from .replies import reply_result
from .actions import remove_nomination
from .models import NominationResult


def run_four_award_sync():
    if not ENABLED:
        return {"status": "disabled"}

    nominations = parse_nominations()

    approved: List[NominationResult] = []
    failed: List[NominationResult] = []
    manual: List[NominationResult] = []

    for nom in nominations[:MAX_NOMINATIONS_PER_RUN]:
        result = review_nomination(nom)

        if result.status == "approved":
            approved.append(result)
            remove_nomination(nom)
            reply_result(nom, result)

        elif result.status == "failed_to_verify":
            failed.append(result)
            reply_result(nom, result)

        else:
            manual.append(result)
            reply_result(nom, result)

    if approved:
        sync_records_table([r.record for r in approved if r.record])

    return {
        "approved": len(approved),
        "failed": len(failed),
        "manual": len(manual),
    }

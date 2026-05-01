from __future__ import annotations

from typing import List

from .config import ENABLED, MAX_NOMINATIONS_PER_RUN
from .parser import parse_nominations
from .reviewer import review_nomination
from .records import sync_records_table
from .replies import reply_result
from .actions import remove_nomination, set_article_history_four
from .models import FourAwardRecord, NominationResult


def _approved_records(results: List[NominationResult]) -> List[FourAwardRecord]:
    records: List[FourAwardRecord] = []
    for result in results:
        if not result.record:
            continue
        for user in result.nomination.users:
            records.append(
                FourAwardRecord(
                    user=user,
                    article=result.record.article,
                    award_date=result.record.award_date,
                    creation_date=result.record.creation_date,
                    dyk_date=result.record.dyk_date,
                    ga_date=result.record.ga_date,
                    fa_date=result.record.fa_date,
                )
            )
    return records


def _should_mark_article_history_no(result: NominationResult) -> bool:
    skip_codes = {"duplicate_record", "missing_article", "missing_article_page"}
    return not any(issue.code in skip_codes for issue in result.issues)


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
            set_article_history_four(nom.article, "yes")
            reply_result(nom, result)

        elif result.status == "failed_to_verify":
            failed.append(result)
            remove_nomination(nom)
            if _should_mark_article_history_no(result):
                set_article_history_four(nom.article, "no")
            reply_result(nom, result)

        else:
            manual.append(result)
            reply_result(nom, result)

    if approved:
        sync_records_table(_approved_records(approved))

    return {
        "approved": len(approved),
        "failed": len(failed),
        "manual": len(manual),
    }

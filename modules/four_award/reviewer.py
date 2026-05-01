from __future__ import annotations

import re
from datetime import date
from typing import Optional

from .config import ALLOW_AUTOMATED_APPROVAL, RECORDS_PAGE
from .models import FourAwardNomination, FourAwardRecord, NominationResult, VerificationIssue
from .util import award_date, clean_wiki_value, date_window, normalize_title, normalize_user, parse_date, to_iso
from .wiki import get_wiki


def _issue(code: str, reason: str) -> VerificationIssue:
    return VerificationIssue(code=code, reason=reason)


def _contains_record(records_text: str, article: str, users: list[str]) -> bool:
    haystack = records_text.replace("_", " ").casefold()
    if normalize_title(article).casefold() not in haystack:
        return False
    return any(normalize_user(user) in haystack for user in users)


def _action_date(text: str, action_name: str) -> Optional[date]:
    value = _action_value(text, action_name)
    return parse_date(value)


def _action_value(text: str, action_name: str) -> str:
    for match in re.finditer(r"\|\s*action(\d+)\s*=\s*([^\n|]+)", text, re.I):
        if action_name.casefold() not in match.group(2).casefold():
            continue
        index = match.group(1)
        date_match = re.search(rf"^\|\s*action{index}date\s*=\s*([^\n]+)", text, re.I | re.M)
        if date_match:
            return date_match.group(1).strip()
    direct = re.search(rf"^\|\s*{re.escape(action_name)}(?:date|_date)?\s*=\s*([^\n]+)", text, re.I | re.M)
    return direct.group(1).strip() if direct else ""


def _action_link(text: str, action_name: str) -> str:
    for match in re.finditer(r"\|\s*action(\d+)\s*=\s*([^\n|]+)", text, re.I):
        if action_name.casefold() not in match.group(2).casefold():
            continue
        index = match.group(1)
        link_match = re.search(rf"^\|\s*action{index}link\s*=\s*([^\n]+)", text, re.I | re.M)
        if link_match:
            return _link_target(link_match.group(1))
    return ""


def _link_target(value: str) -> str:
    match = re.search(r"\[\[([^|\]]+)", value)
    if match:
        return normalize_title(match.group(1))
    return normalize_title(clean_wiki_value(value))


def _article_history_template(text: str) -> str:
    match = re.search(r"\{\{\s*Article history\b.*?\n\}\}", text, re.I | re.S)
    if match:
        return match.group(0)
    match = re.search(r"\{\{\s*Article history\b.*?\}\}", text, re.I | re.S)
    return match.group(0) if match else ""


def _has_fa_status(history: str) -> bool:
    if re.search(r"\|\s*(currentstatus|status)\s*=\s*FA\b", history, re.I):
        return True
    return bool(
        re.search(
            r"\|\s*action\d+\s*=\s*(?:FAC|FAR).*?\|\s*action\d+result\s*=\s*(?:promoted|kept)",
            history,
            re.I | re.S,
        )
    )


def _record_for(nomination: FourAwardNomination, history: str, creation_date: Optional[date]) -> FourAwardRecord:
    dyk_date = _action_value(history, "DYK")
    ga_date = _action_value(history, "GAN") or _action_value(history, "GA")
    fa_date = _action_value(history, "FAC") or _action_value(history, "FA")
    return FourAwardRecord(
        user=nomination.users[0],
        article=nomination.article,
        award_date=award_date(),
        creation_date=to_iso(creation_date),
        dyk_date=dyk_date,
        ga_date=ga_date,
        fa_date=fa_date,
    )


def _missing_users(expected: list[str], evidence: set[str]) -> list[str]:
    normalized = {normalize_user(user) for user in evidence}
    return [user for user in expected if normalize_user(user) not in normalized]


def _signature_users(text: str) -> set[str]:
    users = set()
    for pattern in (
        r"\[\[\s*User:([^|\]/#]+)",
        r"\[\[\s*User talk:([^|\]/#]+)",
        r"\{\{\s*u(?:ser)?\s*\|\s*([^}|]+)",
    ):
        for match in re.finditer(pattern, text, re.I):
            users.add(clean_wiki_value(match.group(1)))
    return users


def _safe_text(title: str) -> str:
    try:
        return get_wiki().get_text(title)
    except Exception:
        return ""


def _process_page_users(title: str, start: date | None = None, end: date | None = None) -> set[str]:
    if not title:
        return set()
    wiki = get_wiki()
    users = wiki.revision_users(title, start=start, end=end)
    users.update(_signature_users(_safe_text(title)))
    return users


def _stage_evidence_users(article: str, process_pages: list[str], start: date | None, end: date | None) -> set[str]:
    wiki = get_wiki()
    users = wiki.revision_users(article, start=start, end=end)
    for page in process_pages:
        users.update(_process_page_users(page, start=start, end=end))
    return users


def _default_dyk_page(nomination: FourAwardNomination) -> str:
    return nomination.dyknom or f"Template:Did you know nominations/{nomination.article}"


def _contribution_issues(nomination: FourAwardNomination, history: str, record: FourAwardRecord) -> list[VerificationIssue]:
    wiki = get_wiki()
    issues: list[VerificationIssue] = []
    creation = wiki.page_creation(nomination.article)
    creation_start, creation_end = date_window(creation.date, 0, 7)
    creation_users = set()
    if creation.user:
        creation_users.add(creation.user)
    creation_users.update(wiki.revision_users(nomination.article, start=creation_start, end=creation_end))

    missing = _missing_users(nomination.users, creation_users)
    if missing:
        issues.append(
            _issue(
                "missing_creation_contribution",
                "Could not verify page creation or early article edits for " + ", ".join(missing) + ".",
            )
        )

    dyk_start = parse_date(record.creation_date)
    dyk_end = parse_date(record.dyk_date)
    ga_start = dyk_end or dyk_start
    ga_end = parse_date(record.ga_date)
    fa_start = ga_end or ga_start
    fa_end = parse_date(record.fa_date)

    checks = (
        (
            "missing_dyk_contribution",
            "DYK",
            [_default_dyk_page(nomination), _action_link(history, "DYK")],
            dyk_start,
            dyk_end,
        ),
        (
            "missing_ga_contribution",
            "GA",
            [_action_link(history, "GAN"), _action_link(history, "GA"), f"Talk:{nomination.article}/GA1"],
            ga_start,
            ga_end,
        ),
        (
            "missing_fa_contribution",
            "FA",
            [_action_link(history, "FAC"), _action_link(history, "FA"), f"Wikipedia:Featured article candidates/{nomination.article}/archive1"],
            fa_start,
            fa_end,
        ),
    )
    for code, label, pages, start, end in checks:
        clean_pages = [page for page in dict.fromkeys(pages) if page]
        evidence_users = _stage_evidence_users(nomination.article, clean_pages, start, end)
        missing = _missing_users(nomination.users, evidence_users)
        if missing:
            issues.append(
                _issue(
                    code,
                    f"Could not verify {label} process-page participation or article edits for " + ", ".join(missing) + ".",
                )
            )
    return issues


def review_nomination(nomination: FourAwardNomination) -> NominationResult:
    if not nomination.article:
        return NominationResult(nomination, "failed_to_verify", [_issue("missing_article", "The nomination does not identify an article.")])
    if not nomination.users:
        return NominationResult(nomination, "manual_review_needed", [_issue("missing_users", "No credited user was supplied; self-nominations need reviewer confirmation.")])

    wiki = get_wiki()
    if not wiki.exists(nomination.article):
        return NominationResult(nomination, "failed_to_verify", [_issue("missing_article_page", f"[[{nomination.article}]] does not exist.")])

    if _contains_record(wiki.get_text(RECORDS_PAGE), nomination.article, nomination.users):
        return NominationResult(nomination, "failed_to_verify", [_issue("duplicate_record", "The article and user already appear in the Four Award records.")])

    history = _article_history_template(wiki.get_text(f"Talk:{nomination.article}"))
    if not history:
        return NominationResult(nomination, "failed_to_verify", [_issue("missing_article_history", "The talk page does not contain {{Article history}} evidence.")])
    if not _has_fa_status(history):
        return NominationResult(nomination, "failed_to_verify", [_issue("not_featured_article", "{{Article history}} does not show current FA status.")])

    creation = wiki.page_creation(nomination.article)
    record = _record_for(nomination, history, creation.date)
    issues: list[VerificationIssue] = []
    for value, label in (
        (record.creation_date, "creation date"),
        (record.dyk_date, "DYK date"),
        (record.ga_date, "GA date"),
        (record.fa_date, "FA date"),
    ):
        if not value:
            issues.append(_issue("missing_milestone", f"Could not determine the {label}."))
    if not issues:
        issues.extend(_contribution_issues(nomination, history, record))

    if issues or not ALLOW_AUTOMATED_APPROVAL:
        if not ALLOW_AUTOMATED_APPROVAL:
            issues.append(_issue("human_judgment_required", "Four Award credit requires reviewer judgment about the editor's contributions at each stage."))
        return NominationResult(nomination, "manual_review_needed", issues, record)

    return NominationResult(nomination, "approved", record=record)

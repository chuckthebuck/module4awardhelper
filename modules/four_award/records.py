from __future__ import annotations

import re
from collections import Counter
from typing import Iterable

from .config import ENABLE_RECORDS, RECORDS_PAGE
from .models import FourAwardRecord
from .util import normalize_user, to_dts
from .wiki import get_wiki


def _record_row(record: FourAwardRecord, ordinal: int) -> str:
    display = record.display_user or record.user
    suffix = f" ({ordinal})" if ordinal > 1 else ""
    return (
        "|-\n"
        f"| [[User:{record.user}|{display}]]{suffix}\n"
        f"| [[{record.article}]]\n"
        f"| {to_dts(record.award_date)}\n"
        f"| {to_dts(record.creation_date)}\n"
        f"| {to_dts(record.dyk_date)}\n"
        f"| {to_dts(record.ga_date)}\n"
        f"| {to_dts(record.fa_date)}"
    )


def _four_awards_table(text: str) -> tuple[int, int] | None:
    heading = re.search(r"^==\s*Four Awards\s*==\s*$", text, re.M | re.I)
    start_search = heading.end() if heading else 0
    table_start = text.find("{|", start_search)
    if table_start < 0:
        return None
    table_end = text.find("|}", table_start)
    if table_end < 0:
        return None
    return table_start, table_end + 2


def _existing_counts(table: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    for match in re.finditer(r"\[\[User:([^|\]]+)", table, re.I):
        counts[normalize_user(match.group(1))] += 1
    return counts


def _insert_rows(table: str, records: list[FourAwardRecord]) -> str:
    counts = _existing_counts(table)
    row_chunks = re.split(r"(?m)(?=^\|-\s*$)", table)
    header = row_chunks[0]
    existing_rows = row_chunks[1:]

    def row_user(row: str) -> str:
        match = re.search(r"\[\[User:([^|\]]+)", row, re.I)
        return normalize_user(match.group(1)) if match else ""

    for record in sorted(records, key=lambda r: (normalize_user(r.user), r.award_date or "")):
        counts[normalize_user(record.user)] += 1
        new_row = _record_row(record, counts[normalize_user(record.user)])
        new_key = normalize_user(record.user)
        inserted = False
        for index, row in enumerate(existing_rows):
            key = row_user(row)
            if key and key > new_key:
                existing_rows.insert(index, new_row + "\n")
                inserted = True
                break
        if not inserted:
            end_index = len(existing_rows)
            for index, row in enumerate(existing_rows):
                if row.strip().endswith("|}"):
                    end_index = index
                    break
            existing_rows.insert(end_index, new_row + "\n")
    return header.rstrip() + "\n" + "".join(existing_rows).rstrip() + "\n"


def sync_records_table(records: Iterable[FourAwardRecord]) -> int:
    records = [record for record in records if record]
    if not records or not ENABLE_RECORDS:
        return 0
    wiki = get_wiki()
    text = wiki.get_text(RECORDS_PAGE)
    span = _four_awards_table(text)
    if not span:
        raise RuntimeError("Could not find the Four Awards records table")
    start, end = span
    new_table = _insert_rows(text[start:end], records)
    wiki.save_text(RECORDS_PAGE, text[:start] + new_table + text[end:], "Update Four Award records")
    return len(records)

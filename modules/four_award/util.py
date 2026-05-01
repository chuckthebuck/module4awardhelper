from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional


def normalize_user(value: str | None) -> str:
    value = (value or "").replace("_", " ").strip()
    value = re.sub(r"\s*\(\d+\)\s*$", "", value)
    return re.sub(r"\s+", " ", value).casefold()


def normalize_title(value: str | None) -> str:
    value = (value or "").replace("_", " ").strip()
    value = re.sub(r"\s+", " ", value)
    return value[:1].upper() + value[1:] if value else ""


def parse_date(value: str | None) -> Optional[date]:
    if not value:
        return None
    value = value.strip()
    m = re.search(r"\{\{\s*dts\s*\|\s*(\d{4})\s*\|\s*(\d{1,2})\s*\|\s*(\d{1,2})", value, re.I)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    for fmt in ("%Y-%m-%d", "%d %B %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None


def to_iso(value: str | date | None) -> str:
    if value is None:
        return ""
    if isinstance(value, date):
        return value.isoformat()
    parsed = parse_date(value)
    return parsed.isoformat() if parsed else value


def to_dts(value: str | date | None) -> str:
    parsed = parse_date(value) if isinstance(value, str) else value
    if not parsed:
        return ""
    return "{{dts|%04d|%02d|%02d}}" % (parsed.year, parsed.month, parsed.day)


def strip_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def one_line(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\n", " ")).strip()

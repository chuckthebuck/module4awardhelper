from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Optional

import requests

from .config import DRY_RUN, EDIT_TAG_LINK, WIKI_API_URL
from .models import PageCreation


try:
    from pywikibot_env import ensure_pywikibot_env
except Exception:  # pragma: no cover - supplied by the framework at runtime
    ensure_pywikibot_env = None

try:
    import pywikibot
except Exception:  # pragma: no cover - supplied by the framework at runtime
    pywikibot = None


@dataclass
class SaveResult:
    title: str
    summary: str
    saved: bool


class WikiClient:
    def __init__(self) -> None:
        self._site = None

    @property
    def site(self):
        if pywikibot is None:
            raise RuntimeError("pywikibot is not available")
        if self._site is None:
            if ensure_pywikibot_env is not None:
                ensure_pywikibot_env(strict=True)
            self._site = pywikibot.Site("en", "wikipedia")
            self._site.login()
        return self._site

    def page(self, title: str):
        return pywikibot.Page(self.site, title)

    def get_text(self, title: str) -> str:
        return self.page(title).text

    def exists(self, title: str) -> bool:
        return bool(self.page(title).exists())

    def first_revision_date(self, title: str) -> Optional[date]:
        return self.page_creation(title).date

    def page_creation(self, title: str) -> PageCreation:
        data = self._query_revisions(
            title,
            {
                "rvlimit": "1",
                "rvdir": "newer",
                "rvprop": "timestamp|user",
            },
        )
        revisions = self._revisions_from_query(data)
        if not revisions:
            return PageCreation(user=None, date=None)
        revision = revisions[0]
        timestamp = _parse_mw_timestamp(revision.get("timestamp"))
        return PageCreation(user=revision.get("user"), date=timestamp.date() if timestamp else None)

    def revision_users(self, title: str, start: date | None = None, end: date | None = None, limit: int = 500) -> set[str]:
        params = {
            "rvlimit": str(max(1, min(limit, 500))),
            "rvprop": "timestamp|user",
            "rvdir": "older",
        }
        if end is not None:
            params["rvstart"] = _mw_timestamp(datetime.combine(end, time.max, timezone.utc))
        if start is not None:
            params["rvend"] = _mw_timestamp(datetime.combine(start, time.min, timezone.utc))
        try:
            data = self._query_revisions(title, params)
        except requests.RequestException:
            return set()
        return {revision["user"] for revision in self._revisions_from_query(data) if revision.get("user")}

    def page_exists(self, title: str) -> bool:
        params = {
            "action": "query",
            "titles": title,
            "format": "json",
            "formatversion": "2",
        }
        data = requests.get(WIKI_API_URL, params=params, timeout=20).json()
        pages = data.get("query", {}).get("pages", [])
        return bool(pages and not pages[0].get("missing"))

    def _query_revisions(self, title: str, revision_params: dict[str, str]) -> dict:
        params = {
            "action": "query",
            "prop": "revisions",
            "titles": title,
            "format": "json",
            "formatversion": "2",
        }
        params.update(revision_params)
        response = requests.get(WIKI_API_URL, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def _revisions_from_query(self, data: dict) -> list[dict]:
        pages = data.get("query", {}).get("pages", [])
        if not pages or pages[0].get("missing"):
            return []
        return pages[0].get("revisions") or []

    def save_text(self, title: str, text: str, summary: str) -> SaveResult:
        summary = f"{summary} {EDIT_TAG_LINK}".strip()
        if DRY_RUN:
            return SaveResult(title=title, summary=summary, saved=False)
        page = self.page(title)
        if page.text == text:
            return SaveResult(title=title, summary=summary, saved=False)
        page.text = text
        page.save(summary=summary, bot=True)
        return SaveResult(title=title, summary=summary, saved=True)


_client = WikiClient()


def get_wiki() -> WikiClient:
    return _client


def _parse_mw_timestamp(value: str | None) -> Optional[datetime]:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _mw_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

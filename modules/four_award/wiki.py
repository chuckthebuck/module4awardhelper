from __future__ import annotations

from typing import Optional

import requests

API = "https://en.wikipedia.org/w/api.php"


class Wiki:
    def __init__(self, user_agent: str = "FourAwardHelper/0.1") -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

    def get_wikitext(self, title: str) -> tuple[str, Optional[int]]:
        params = {
            "action": "query",
            "prop": "revisions",
            "rvprop": "content|ids",
            "rvslots": "main",
            "format": "json",
            "titles": title,
        }
        r = self.session.get(API, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        pages = data.get("query", {}).get("pages", {})
        for p in pages.values():
            revs = p.get("revisions")
            if not revs:
                return "", None
            rev = revs[0]
            text = rev.get("slots", {}).get("main", {}).get("*") or rev.get("*") or ""
            return text, rev.get("revid")
        return "", None

    def edit(self, title: str, text: str, summary: str, baserevid: Optional[int] = None) -> None:
        raise NotImplementedError("Editing requires OAuth; not enabled in this environment")

    def append_section(self, title: str, section: int, text: str, summary: str) -> None:
        raise NotImplementedError("Editing requires OAuth; not enabled in this environment")

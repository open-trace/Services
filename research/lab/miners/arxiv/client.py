from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
ARXIV_API = "http://export.arxiv.org/api/query"
ARXIV_RATE_LIMIT_S = 3.0


@dataclass(frozen=True)
class ArxivEntry:
    arxiv_id: str
    title: str
    abstract: str
    authors: list[str]
    categories: list[str]
    published: str
    pdf_url: str
    abs_url: str


def _text(el: ET.Element | None) -> str:
    if el is None or el.text is None:
        return ""
    return el.text.strip()


def _parse_entry(entry: ET.Element) -> ArxivEntry | None:
    id_url = _text(entry.find("atom:id", ATOM_NS))
    if not id_url:
        return None
    arxiv_id = id_url.rstrip("/").split("/abs/")[-1]
    if not arxiv_id:
        return None

    authors: list[str] = []
    for author in entry.findall("atom:author", ATOM_NS):
        name = _text(author.find("atom:name", ATOM_NS))
        if name:
            authors.append(name)

    categories: list[str] = []
    for cat in entry.findall("atom:category", ATOM_NS):
        term = cat.get("term")
        if term:
            categories.append(term)

    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    abs_url = f"https://arxiv.org/abs/{arxiv_id}"

    return ArxivEntry(
        arxiv_id=arxiv_id,
        title=_text(entry.find("atom:title", ATOM_NS)),
        abstract=_text(entry.find("atom:summary", ATOM_NS)),
        authors=authors,
        categories=categories,
        published=_text(entry.find("atom:published", ATOM_NS)),
        pdf_url=pdf_url,
        abs_url=abs_url,
    )


def fetch_page(
    client: httpx.Client,
    query: str,
    *,
    start: int = 0,
    max_results: int = 100,
) -> tuple[list[ArxivEntry], int]:
    """Fetch one page from arXiv Atom API. Returns entries and total results reported."""
    params = {
        "search_query": query,
        "start": start,
        "max_results": min(max_results, 2000),
    }
    url = f"{ARXIV_API}?{urlencode(params)}"
    resp = client.get(url, timeout=60.0)
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    total_el = root.find("{http://a9.com/-/spec/opensearch/1.1/}totalResults")
    total = int(_text(total_el) or "0")

    entries: list[ArxivEntry] = []
    for entry_el in root.findall("atom:entry", ATOM_NS):
        parsed = _parse_entry(entry_el)
        if parsed:
            entries.append(parsed)
    return entries, total


def iter_entries(
    client: httpx.Client,
    query: str,
    *,
    max_results: int,
    rate_limit_s: float = ARXIV_RATE_LIMIT_S,
) -> list[ArxivEntry]:
    """Paginate arXiv API until max_results entries collected."""
    collected: list[ArxivEntry] = []
    start = 0
    page_size = min(100, max_results)

    while len(collected) < max_results:
        batch, _total = fetch_page(client, query, start=start, max_results=page_size)
        if not batch:
            break
        for entry in batch:
            collected.append(entry)
            if len(collected) >= max_results:
                break
        start += len(batch)
        if len(batch) < page_size:
            break
        time.sleep(rate_limit_s)

    return collected[:max_results]


def download_pdf(client: httpx.Client, pdf_url: str) -> bytes:
    resp = client.get(pdf_url, timeout=120.0, follow_redirects=True)
    resp.raise_for_status()
    return resp.content


def entry_to_meta(entry: ArxivEntry) -> dict[str, Any]:
    return {
        "source": "arxiv",
        "arxiv_id": entry.arxiv_id,
        "title": entry.title,
        "abstract": entry.abstract,
        "authors": entry.authors,
        "categories": entry.categories,
        "published": entry.published,
        "pdf_url": entry.pdf_url,
        "abs_url": entry.abs_url,
    }

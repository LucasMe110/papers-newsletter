import os
import xml.etree.ElementTree as ET
import httpx

ARXIV_CATEGORIES = ["cs.AI", "cs.LG", "cs.CL", "cs.SE", "cs.CV", "cs.HC", "econ.GN"]
ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_API_URL = "http://export.arxiv.org/api/query"


def fetch_arxiv_papers(category: str, max_results: int = 3) -> list[dict]:
    url = (
        f"{ARXIV_API_URL}?search_query=cat:{category}"
        f"&sortBy=submittedDate&sortOrder=descending&max_results={max_results}"
    )
    try:
        response = httpx.get(url, timeout=30)
        response.raise_for_status()
        root = ET.fromstring(response.text)
        papers = []
        for entry in root.findall(f"{ATOM_NS}entry"):
            title = (entry.findtext(f"{ATOM_NS}title") or "").strip()
            abstract = (entry.findtext(f"{ATOM_NS}summary") or "").strip()[:800]
            published = (entry.findtext(f"{ATOM_NS}published") or "")[:10]
            authors = [
                (a.findtext(f"{ATOM_NS}name") or "").strip()
                for a in entry.findall(f"{ATOM_NS}author")
            ]
            link = entry.findtext(f"{ATOM_NS}id") or ""
            if not title:
                continue
            papers.append({
                "title": title,
                "abstract": abstract,
                "authors": authors,
                "published": published,
                "link": link,
                "source": "arxiv",
                "category": category,
            })
        return papers
    except Exception as e:
        print(f"  [AVISO] Falha ao coletar arXiv/{category}: {e}")
        return []


def fetch_all_arxiv_papers(max_per_category: int = 3) -> list[dict]:
    papers = []
    for category in ARXIV_CATEGORIES:
        batch = fetch_arxiv_papers(category, max_per_category)
        papers.extend(batch)
    return papers

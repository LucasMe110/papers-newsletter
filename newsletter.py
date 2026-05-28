import json
import os
import xml.etree.ElementTree as ET
import anthropic
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


HF_PAPERS_URL = "https://huggingface.co/api/daily_papers"


def fetch_hf_papers(max_results: int = 6) -> list[dict]:
    try:
        response = httpx.get(HF_PAPERS_URL, timeout=30)
        response.raise_for_status()
        data = response.json()
        papers = []
        for item in data[:max_results]:
            paper = item.get("paper", {})
            title = (paper.get("title") or "").strip()
            abstract = (paper.get("summary") or "").strip()[:800]
            published = (item.get("publishedAt") or "")[:10]
            authors = [a.get("name", "") for a in paper.get("authors", [])]
            paper_id = paper.get("id", "")
            if paper_id and paper_id.replace(".", "").replace("-", "").isdigit() or (len(paper_id) > 4 and paper_id[4] == "."):
                link = f"https://arxiv.org/abs/{paper_id}"
            else:
                link = f"https://huggingface.co/papers/{paper_id}"
            if not title:
                continue
            papers.append({
                "title": title,
                "abstract": abstract,
                "authors": authors,
                "published": published,
                "link": link,
                "source": "huggingface",
                "category": "hf-daily",
            })
        return papers
    except Exception as e:
        print(f"  [AVISO] Falha ao coletar HF Daily Papers: {e}")
        return []


MAX_PAPERS = 12


def deduplicate_papers(papers: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for paper in papers:
        key = paper["title"].lower().strip()[:60]
        if key not in seen:
            seen.add(key)
            unique.append(paper)
    return unique


def collect_all_papers() -> list[dict]:
    print("[1/4] Coletando papers...")
    arxiv_papers = fetch_all_arxiv_papers(max_per_category=3)
    hf_papers = fetch_hf_papers(max_results=6)
    all_papers = arxiv_papers + hf_papers
    unique = deduplicate_papers(all_papers)
    selected = unique[:MAX_PAPERS]
    print(f"[2/4] {len(selected)} papers após deduplicação (de {len(all_papers)} coletados)")
    return selected


SUMMARIZE_PROMPT = """Você é um assistente de curadoria acadêmica. Para cada paper abaixo, gere em português brasileiro:
1. Um resumo de 2 a 3 frases claro e direto
2. Uma frase de relevância prática ("Por que importa:")
3. O nível de complexidade: Iniciante, Intermediário ou Avançado

Responda com um JSON array, um objeto por paper, na mesma ordem dos papers fornecidos:
[
  {{"index": 0, "resumo": "...", "relevancia": "...", "nivel": "Intermediário"}},
  ...
]

Responda APENAS com o JSON, sem markdown, sem explicações adicionais.

Papers:
{papers_text}"""


def summarize_papers(papers: list[dict]) -> list[dict]:
    print("[3/4] Sumarizando papers com Claude...")
    papers_text = ""
    for i, p in enumerate(papers):
        authors_str = ", ".join(p["authors"][:3])
        if len(p["authors"]) > 3:
            authors_str += " et al."
        papers_text += f"[{i}] Título: {p['title']}\nAutores: {authors_str}\nAbstract: {p['abstract']}\n\n"

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": SUMMARIZE_PROMPT.format(papers_text=papers_text)}],
    )
    raw = message.content[0].text.strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        summaries = json.loads(raw)
        summary_map = {item["index"]: item for item in summaries}
    except Exception as e:
        print(f"  [AVISO] Falha ao parsear JSON do Claude: {e}")
        summary_map = {}

    enriched = []
    for i, paper in enumerate(papers):
        s = summary_map.get(i, {})
        enriched.append({
            **paper,
            "resumo": s.get("resumo", "Resumo não disponível"),
            "relevancia": s.get("relevancia", ""),
            "nivel": s.get("nivel", "Intermediário"),
        })
    return enriched

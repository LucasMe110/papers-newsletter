"""
Weekly academic paper newsletter — collects papers from arXiv and Hugging Face,
summarizes them in Brazilian Portuguese via Claude, and sends an HTML email via Resend.

Usage: python3 newsletter.py (requires ANTHROPIC_API_KEY, RESEND_API_KEY, EMAIL_FROM, EMAIL_TO)
"""
import json
import os
import xml.etree.ElementTree as ET
import anthropic
import httpx

ARXIV_CATEGORIES = ["cs.AI", "cs.LG", "cs.CL", "cs.SE", "cs.CV", "cs.HC", "econ.GN"]
# arXiv API responses are Atom XML — all elements must be prefixed with this namespace
ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_API_URL = "https://export.arxiv.org/api/query"


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

    # All papers are sent in a single API call to minimize latency and cost
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


CATEGORY_NAMES = {
    "cs.AI": "IA & Machine Learning",
    "cs.LG": "IA & Machine Learning",
    "cs.CL": "LLMs & NLP",
    "cs.SE": "Engenharia de Software",
    "cs.CV": "Visão Computacional",
    "cs.HC": "HCI & Produto",
    "econ.GN": "Negócios & Produto",
    "hf-daily": "LLMs & IA Generativa",
}


def render_email(papers: list[dict], edition_date: str) -> str:
    papers_html = ""
    for paper in papers:
        category_name = CATEGORY_NAMES.get(paper["category"], paper["category"])
        authors_str = ", ".join(paper["authors"][:3])
        if len(paper["authors"]) > 3:
            authors_str += " et al."

        relevancia_html = ""
        if paper.get("relevancia"):
            relevancia_html = f'<p style="font-size:14px;color:#4B5563;font-style:italic;margin:0 0 10px 0;">{paper["relevancia"]}</p>'

        papers_html += f"""
        <div style="margin-bottom:32px;">
          <p style="font-size:12px;color:#9CA3AF;margin:0 0 4px 0;">{category_name} &nbsp;·&nbsp; {paper["nivel"]}</p>
          <p style="font-size:15px;color:#111827;margin:0 0 6px 0;"><strong>{paper["title"]}</strong></p>
          <p style="font-size:13px;color:#6B7280;margin:0 0 10px 0;">{authors_str} &nbsp;·&nbsp; {paper["published"]}</p>
          <p style="font-size:15px;color:#111827;line-height:1.65;margin:0 0 10px 0;">{paper["resumo"]}</p>
          {relevancia_html}<a href="{paper["link"]}" style="font-size:13px;color:#4F46E5;text-decoration:underline;">Ler paper completo →</a>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#FFFFFF;font-family:Georgia,serif;">
  <div style="max-width:600px;margin:0 auto;padding:40px 24px;">
    <p style="font-size:13px;color:#9CA3AF;margin:0 0 40px 0;">Papers da Semana &nbsp;·&nbsp; {edition_date}</p>
    {papers_html}
    <p style="font-size:12px;color:#9CA3AF;margin:48px 0 0 0;">Você recebe este email porque se inscreveu na Papers Newsletter.</p>
  </div>
</body>
</html>"""


def send_email(html_content: str, subject: str) -> None:
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    gmail_user = os.environ["EMAIL_FROM"].strip()
    # A App Password do Google é exibida com espaços ("abcd efgh ijkl mnop").
    # Se for colada com espaços ou aspas no secret, o login falha com BadCredentials.
    app_password = os.environ["GMAIL_APP_PASSWORD"].strip().strip('"').strip("'").replace(" ", "")
    recipients = [e.strip() for e in os.environ["EMAIL_RECIPIENTS"].split(",")]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html_content, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, app_password)
        server.sendmail(gmail_user, recipients, msg.as_string())

    print(f"[4/4] Email enviado para {len(recipients)} destinatário(s)!")


def main() -> None:
    import datetime
    today = datetime.date.today()
    edition_date = today.strftime("%d/%m/%Y")

    papers = collect_all_papers()
    if not papers:
        raise RuntimeError("Nenhum paper coletado — abortando.")

    papers = summarize_papers(papers)

    subject = f"Papers da Semana · {edition_date} · {len(papers)} papers selecionados"
    html = render_email(papers, edition_date)
    send_email(html, subject)


if __name__ == "__main__":
    main()

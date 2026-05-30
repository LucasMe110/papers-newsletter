# papers-newsletter

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A self-hosted weekly newsletter that automatically collects, summarizes, and delivers academic papers to your inbox — in Brazilian Portuguese.

Every Tuesday at 8am (Brasília time), it fetches the latest papers from arXiv and Hugging Face Daily Papers, summarizes each one using Claude, and sends a clean editorial-style email via Resend.

---

## What it does

- Fetches up to 12 papers per week across 7 arXiv categories (AI, ML, NLP, SE, CV, HCI, Economics) + Hugging Face Daily Papers
- Deduplicates papers across sources
- Summarizes each paper in a single Claude API call: 2–3 sentence summary in PT-BR, practical relevance, and complexity level (Beginner / Intermediate / Advanced)
- Sends a clean, readable HTML email — no banners, no colored buttons, just text

## How it works

```
1. Collect  →  arXiv API (7 categories × 3 papers) + HF Daily Papers (6 papers)
2. Dedupe   →  removes duplicates by title similarity, caps at 12 papers
3. Summarize→  single Claude API call returns PT-BR summaries as JSON
4. Send     →  renders HTML email and posts to Resend API
```

Total runtime: ~1 minute. Total cost: ~US$0.50/month.

## Prerequisites

You'll need free accounts on:

| Service | Purpose | Cost |
|---|---|---|
| [Anthropic](https://console.anthropic.com) | Claude API for summarization | ~US$0.50/month |
| [Resend](https://resend.com) | Email delivery | Free (3,000 emails/month) |
| [GitHub](https://github.com) | Hosting + scheduled execution | Free |

## Setup

**1. Fork or clone this repository**

```bash
git clone https://github.com/LucasMe110/papers-newsletter.git
cd papers-newsletter
```

**2. Get your API keys**

- **Anthropic:** go to [console.anthropic.com](https://console.anthropic.com) → API Keys → Create Key
- **Resend:** go to [resend.com](https://resend.com) → API Keys → Create API Key

**3. Configure environment variables**

```bash
cp .env.example .env
# edit .env with your keys
```

**4. Add secrets to GitHub Actions**

Go to your repo → Settings → Secrets and variables → Actions, and add:

| Secret | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic key (`sk-ant-...`) |
| `RESEND_API_KEY` | Your Resend key (`re_...`) |
| `EMAIL_FROM` | Sender address (see note below) |
| `EMAIL_TO` | Your email address |

> **Note on `EMAIL_FROM`:** Without a verified domain on Resend, use `onboarding@resend.dev` — but you can only send to the email registered on your Resend account. To send to any address, [verify a domain](https://resend.com/domains).

**5. Test it**

Trigger a manual run from the Actions tab:

```bash
gh workflow run newsletter.yml
```

Or go to **Actions → Papers Newsletter → Run workflow** on GitHub.

## Running locally

```bash
cp .env.example .env
# fill in your keys

# run with uv (no install needed)
uv run --with anthropic --with httpx python3 newsletter.py

# or install dependencies first
pip install -r requirements.txt
python3 newsletter.py
```

## Configuration

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude |
| `RESEND_API_KEY` | Resend API key for email delivery |
| `EMAIL_FROM` | Sender address (must be verified on Resend) |
| `EMAIL_TO` | Recipient address |

To change the schedule, edit the cron expression in `.github/workflows/newsletter.yml`:

```yaml
- cron: '0 11 * * 2'  # Every Tuesday at 11:00 UTC (08:00 Brasília)
```

## Cost

| Component | Cost |
|---|---|
| Claude API (~4 runs/month) | ~US$0.20–0.50 |
| Resend | Free |
| GitHub Actions | Free |
| **Total** | **< US$1.00/month** |

## License

MIT — see [LICENSE](LICENSE).

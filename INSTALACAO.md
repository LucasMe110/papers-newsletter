# Instalação — Papers Newsletter

Guia passo a passo para colocar a newsletter em produção. Tempo estimado: **15 minutos**.

---

## O que você vai precisar

| Conta | Para quê | Custo |
|---|---|---|
| [GitHub](https://github.com) | Hospedar o código e rodar o pipeline automaticamente | Gratuito |
| [Anthropic](https://console.anthropic.com) | API do Claude para resumir os papers em PT-BR | ~US$ 0,50/mês |
| [Resend](https://resend.com) | Enviar o email semanal | Gratuito (até 3.000 emails/mês) |

---

## Passo 1 — Criar o repositório no GitHub

1. Acesse [github.com/new](https://github.com/new)
2. Preencha:
   - **Repository name:** `papers-newsletter`
   - **Visibility:** Private (recomendado)
   - **NÃO** inicialize com README, .gitignore ou licença
3. Clique em **Create repository**
4. Copie a URL do repositório (ex: `https://github.com/seu-usuario/papers-newsletter.git`)

Agora faça o push do código local:

```bash
cd /home/lucas/workspace/papers
git remote add origin https://github.com/seu-usuario/papers-newsletter.git
git push -u origin main
```

---

## Passo 2 — Obter a chave da API Anthropic

1. Acesse [console.anthropic.com](https://console.anthropic.com)
2. No menu lateral, clique em **API Keys**
3. Clique em **Create Key**, dê um nome (ex: `papers-newsletter`) e copie a chave
4. Guarde o valor — começa com `sk-ant-...`

> Se for a primeira vez, você precisará adicionar créditos. US$ 5 dura vários meses de uso.

---

## Passo 3 — Criar conta no Resend e verificar domínio

1. Acesse [resend.com](https://resend.com) e crie uma conta gratuita
2. Vá em **API Keys → Create API Key** e copie a chave
3. Para o remetente (`EMAIL_FROM`), você tem duas opções:
   - **Com domínio próprio:** vá em **Domains → Add Domain** e siga as instruções para adicionar os registros DNS. Use `newsletter@seudominio.com` como remetente.
   - **Sem domínio (só para testes):** use `onboarding@resend.dev` como remetente — funciona apenas para enviar ao seu próprio email cadastrado no Resend.

---

## Passo 4 — Configurar os Secrets no GitHub

Acesse: `https://github.com/seu-usuario/papers-newsletter/settings/secrets/actions`

Clique em **New repository secret** e adicione os 4 secrets abaixo:

| Secret | Valor |
|---|---|
| `ANTHROPIC_API_KEY` | A chave que começa com `sk-ant-...` |
| `RESEND_API_KEY` | A chave do Resend |
| `EMAIL_FROM` | Ex: `newsletter@seudominio.com` ou `onboarding@resend.dev` |
| `EMAIL_TO` | Seu email pessoal (onde você quer receber) |

---

## Passo 5 — Testar manualmente

1. No repositório, clique na aba **Actions**
2. No menu lateral esquerdo, clique em **Papers Newsletter**
3. Clique em **Run workflow → Run workflow**
4. Aguarde ~2-3 minutos e verifique sua caixa de entrada

Se tiver erro, clique no job para ver os logs — o script imprime cada etapa claramente.

---

## Funcionamento automático

Depois do setup, a newsletter roda **toda segunda-feira às 08h (horário de Brasília)** sem nenhuma ação sua.

O agendamento está configurado em `.github/workflows/newsletter.yml`:

```yaml
schedule:
  - cron: '0 11 * * 1'   # 11h UTC = 08h Brasília
```

---

## Custos esperados

| Componente | Custo |
|---|---|
| Claude API (4 execuções/mês) | ~US$ 0,20–0,60 |
| Resend | Gratuito |
| GitHub Actions | Gratuito |
| **Total** | **< US$ 1,00/mês** |

---

## Problemas comuns

**Email caiu no spam**
Verifique se o domínio no Resend tem os registros SPF e DKIM configurados corretamente.

**Erro `ANTHROPIC_API_KEY not found`**
O secret não foi adicionado corretamente no GitHub. Verifique o nome exato (sem espaços).

**Workflow não aparece na aba Actions**
O arquivo `.github/workflows/newsletter.yml` precisa estar na branch `main`. Confirme com `git log --oneline`.

**Nenhum paper coletado**
A API do arXiv pode estar instável. Rode novamente em alguns minutos — o script trata falhas por categoria individualmente.

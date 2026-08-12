# ⚖️ HuquqiyAI — a legal AI assistant for Uzbekistan

A web application that answers a citizen's legal question with three things:
the **verbatim text of the law**, a **practical recommendation**, and **which
state body to contact**. No registration — it works the moment you open it.

Built as a prototype for the President AI Award 2026.

🌐 **Live:** https://huquqiyai-kjpa.onrender.com
🇺🇿 **O'zbekcha:** [README.md](README.md)

---

## At a glance

| | |
|---|---|
| **Problem** | A citizen looking up a legal question hits two walls: the language of the law is impenetrable, and online advice has no source. |
| **Solution** | Every answer has three parts: the **verbatim article**, a plain-language recommendation, and the **exact authority** to contact. |
| **Core guarantee** | Article text **never passes through the AI model**. It is served straight from the database, so silently rewriting the law is technically impossible. |
| **Corpus** | 602 articles/clauses across 15 legal documents, all imported from [lex.uz](https://lex.uz), each with a direct link |
| **Languages** | Uzbek Latin, Uzbek Cyrillic and Russian — the answer follows the script of the question |
| **Quality gate** | 427 automated tests; they make no network calls at all |

---

## Why the answers can be trusted

The central risk in legal AI is a model paraphrasing the law into something
that sounds right and is wrong. That risk is removed **architecturally**, not
by prompting:

- **The model only picks which article applies** (as an ID). It never writes
  the article text. The text reaches the user from `data/qonunlar.json`.
- **Invented IDs are dropped.** If the model returns an article ID that is not
  in the database, it is discarded before the user sees anything.
- **Nothing is written by hand or by AI.** Every article was imported from
  lex.uz by `tools/lex_import.py`. Text that could not be retrieved is marked
  `needs_verification` and displayed as a link only, never as invented text.
- **The parts that must be exact contain no AI at all.** The complaint-letter
  generator and the traffic-fine deadline arithmetic are ordinary code: an
  article and an authority come from the database, dates are subtracted. A
  model that miscounts one day would make a citizen either file a baseless
  appeal or abandon a valid one.

### How this is enforced

The guarantee is not a promise in a document — it is checked by the test
suite. Tests assert that every article ID returned in live runs exists in the
database, that each of the 12 legal topics maps to a real authority, and that
realistic questions retrieve the correct code.

---

## What it does

- **Chat, two registers** — *plain* (everyday language) and *pro* (legal
  register: procedural deadlines, document types, jurisdiction).
- **Document analysis** — upload a PDF/DOCX/TXT and get a legal reading, plus
  **what to check in it** and **how to have it overturned**: the deadline, the
  authority and the procedure, tailored to the document type (court ruling,
  fine, dismissal order, contract, official reply).
- **Contract analysis** — upload an employment, rental, loan or sale contract;
  each clause is returned with a risk level (🔴 unlawful · 🟡 disadvantageous ·
  🟢 worth noting) and the article of law behind that judgment.
- **Traffic-fine legality check** — evaluates a fine against statutory
  deadlines and formalities. **No AI, deliberately** — it is date arithmetic,
  answers in ~0.04 s, and keeps working when every AI provider is down.
- **Speed-camera and radar checks** — including the 5 km/h measurement
  allowance that is most often overlooked, and the road-patrol regulations
  under which a fine issued from an improperly deployed radar carries no legal
  force at all.
- **Complaint / statement-of-claim generator** — one click after a grounded
  answer produces a ready draft. Built without AI; the only blank left for the
  user is the signature.
- **Voice** — ask by microphone on the site and in the Telegram bot; answers
  can be returned as audio.
- **Telegram bot** — text, voice message or document, sharing the exact same
  answer pipeline as the website.
- **Admin page** — add and update articles, and see usage statistics split
  between website and bot, including the list of questions that found no
  answer (used to decide what to add to the corpus next).

---

## Reliability

### An eight-step provider chain

If one provider fails — exhausted credit, a per-minute limit, a network error
— the next one answers and the user notices nothing. The order follows cost:
free backups first, the paid provider last, so money is only spent once every
free quota is gone.

| # | Step | Role |
|---|---|---|
| 1 | Anthropic `claude-sonnet-4-5` | primary, highest quality |
| 2-3 | Google Gemini (2 models) | free backup |
| 4-5 | Groq `gpt-oss-120b` / `20b` | free, large daily quota |
| 6 | OpenRouter `nemotron-3-super` | free, **20 req/min** — for traffic peaks |
| 7 | BazaarLink `auto:free` | free, 10 req/min |
| 8 | OpenAI `gpt-5.4-mini` | paid, last resort |

**Every model is its own step**, because rate limits are counted per model —
measured: when one Groq model was down to 4,323 remaining tokens, the other
still had 7,924. Adding a model to the list therefore multiplies free
capacity; `GEMINI_MODEL` and `GROQ_MODEL` accept a comma-separated list.

Steps 6 and 7 sit at the end on purpose. Their daily quotas are small but
their per-minute limits are wide, so they are held in reserve for the moment
when a burst of simultaneous questions arrives.

Any model added to the chain must first pass two checks: strict `json_schema`
support and coherent Uzbek output. Several candidates were rejected on exactly
these grounds.

### What the user sees when a limit is hit

The message is specific — *"too many requests, try again in 47 seconds"* —
and the number comes from the provider's own response rather than a guess. If
the wait is short (under 8 seconds) the system waits and retries by itself, so
the user never sees an error at all.

A **permanent** failure such as exhausted credit takes that provider out of
rotation for 10 minutes. This avoids a pointless round-trip on every question
and, more importantly, stops a billing error from masking another provider's
merely temporary one.

### Answer cache

A repeated question never reaches an AI provider. The cache has two layers:
memory (no network, ~0 ms) and Upstash (survives restarts). Measured on the
live site: **11.07 s → 0.128 s**.

The cache can be filled ahead of a demo, so the most likely questions are
served instantly and consume no quota:

```bash
python -m tools.kesh_isit            # 69 realistic questions across 11 topics
python -m tools.kesh_isit --moddalar # plus 400+ derived from article titles
```

### Observability

[`/health`](https://huquqiyai-kjpa.onrender.com/health) reports every step of
the chain in order, with its current state, plus whether the answer cache is
persistent. The order itself is information: it shows at a glance that the
paid provider really is last.

---

## The corpus: 602 articles, 15 documents

| Document | Articles | Coverage |
|---|---|---|
| Traffic Regulations | 186 | speed, overtaking, stopping, intersections, level crossings |
| Code of Administrative Liability | 79 | fines, traffic offences, and the fine procedure itself |
| Labour Code | 49 | dismissal, wages, leave, probation, labour disputes |
| Civil Code | 42 | contracts, unjust enrichment, damages, limitation periods |
| Family Code | 34 | alimony, division of property, custody |
| Tax Code | 33 | personal taxation, taxpayer rights |
| Land Code | 31 | plots, leases, seizure for public needs |
| Constitution | 28 | fundamental rights |
| Civil Procedure Code | 28 | filing a claim, appeals |
| Consumer Protection Act | 18 | defective goods, returns, guarantees |
| Housing Code | 18 | ownership, common property, eviction |
| Criminal Code | 16 | theft, fraud, liability |
| Citizens' Appeals Act | 16 | petitioning a state body, response deadlines |
| Road Traffic Act | 12 | general traffic law |
| Road-Patrol Service Regulations | 12 | radar deployment rules |

**Total: 602 articles across 15 documents.**

Tags that drive retrieval are curated by hand: the importer suggests them from
article titles, but real users write words like *tomorqa* (household plot) that
never appear in a heading. Retrieval quality is guarded by tests built from
real questions.

---

**One provider key is enough** to run the whole application — any of
`ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY` or
`BAZAARLINK_API_KEY`. The more you supply, the longer the fallback chain.

Tests:

```bash
python -m pytest tests/ -q     # 427 tests, no network access
```

---


---

## Limitations

Stated plainly, because they matter for judging this honestly:

- **Retrieval is lexical** (BM25 plus curated tags), not semantic. A question
  worded with no vocabulary in common with the article may not find it.
- **The corpus is 15 documents**, not the full body of Uzbek law. Questions
  outside it are answered with an explicit "this is not in the database"
  rather than a guess.
- **Free-tier capacity is finite.** The chain handles bursts of roughly 30
  questions per minute; sustained heavier load needs a paid provider.
- **lex.uz changes are not tracked automatically.** The importer has a
  `--tekshir` mode, but it is run manually.

---

## Disclaimer

HuquqiyAI provides general information and does not replace professional legal
advice. The authoritative source is [lex.uz](https://lex.uz).

Licensed under Apache 2.0.

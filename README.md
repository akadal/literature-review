# Literature Reviewer

Grounded literature-review toolkit that combines Web of Science and Scopus searches,
deduplicates records, cross-checks DOI/title/year evidence, and writes a review report
that only uses source-backed article facts.

The repository includes:

- `wos_search`: copied from the sibling `wos-search` project.
- `scopus_search`: copied from the sibling `scopus-search` project.
- `literature_reviewer`: the orchestration, normalization, cross-check, export, and
  guardrail layer.

## Install

```bash
pip install -e ".[dev]"
cp .env.example .env
```

Set real credentials in `.env`. The real `.env` file is intentionally ignored by git.

Required for live searches:

```env
WOS_API_KEY=...
SCOPUS_API_KEY=...
```

Optional:

```env
SCOPUS_INSTTOKEN=...
UNPAYWALL_EMAIL=...
```

## Quick Use

```bash
literature-review doctor
literature-review search --topic "blockchain tourism" --year-range 2020-2026 --max-results 25
```

A multi-word `--topic` is AND-joined (`TS=(blockchain AND tourism)`), not searched as an exact
phrase, because phrase-wrapping silently collapses recall. Quote the topic yourself when you do
want a phrase: `--topic '"digital natives"'`. Topics containing boolean operators, parentheses or
wildcards are passed through untouched.

Outputs are written under `output/literature_review/` by default:

- `review.md`: grounded review report.
- `articles.csv`: normalized evidence ledger.
- `evidence_groups.json`: deduplicated cross-check groups.
- `diagnostics.json`: run configuration, diagnostics, and export paths.

## Raw Provider Queries

```bash
literature-review search \
  --wos-query 'TS=("large language models" AND education)' \
  --scopus-query 'TITLE-ABS-KEY("large language models" AND education)' \
  --year-range 2021-2026 \
  --max-results 100
```

## Review Existing Exports

```bash
literature-review review-files path/to/wos.csv path/to/scopus.csv --topic "my topic"
```

## Guardrail Philosophy

This tool does not ask an LLM to invent a narrative by default. It builds a deterministic
report from the evidence ledger. Article-level lines include evidence IDs such as
`WOS:...` and `SCOPUS:...`; source-only records are explicitly marked as not confirmed by
the other index.

That does not make research judgment automatic. It makes every generated statement
auditable.

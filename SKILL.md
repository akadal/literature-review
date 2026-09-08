# Literature Reviewer Skill

Use this repository when the user asks for a literature review, systematic scan, WoS
search, Scopus search, or source-grounded research brief.

## Operating Rules

1. Load credentials from `.env`; never print API key values.
2. Prefer both WoS and Scopus unless the user asks for one source.
3. Use raw provider syntax when the user gives it; otherwise build a simple topic query:
   - WoS: `TS=(word1 AND word2)`
   - Scopus: `TITLE-ABS-KEY(word1 AND word2)`
   Multi-word topics are AND-joined, never wrapped as an exact phrase: phrase-wrapping
   silently collapses recall (`"blockchain tourism"` returns 2 Scopus / 1 WoS record;
   `blockchain AND tourism` returns 774 / 95). For a deliberate phrase, quote it inside
   the topic: `--topic '"digital natives"'`.
4. Every article-level claim must be tied to evidence IDs from `articles.csv` or
   `evidence_groups.json`.
5. Treat DOI matches across WoS and Scopus as strongest confirmation.
6. If there is no DOI, use title/year similarity and say that the match is weaker.
7. Do not present a source-only record as cross-source confirmed.
8. Do not infer findings that are not visible in titles, abstracts, journals, years,
   citations, keywords, or other exported fields.
9. Put uncertainty and missing data in the report instead of smoothing it away.

## Standard Command

```bash
literature-review search --topic "<topic>" --year-range "<YYYY-YYYY>" --max-results 50
```

Then read:

- `output/literature_review/review.md`
- `output/literature_review/articles.csv`
- `output/literature_review/evidence_groups.json`
- `output/literature_review/diagnostics.json`

## Reusable Prompt

Ask Codex:

> Use `D:\repos\literature-review` as the literature reviewer. Run both WoS and
> Scopus for `<topic>`, cross-check DOI/title/year evidence, and write only claims
> that are backed by evidence IDs. Report gaps and source-only records separately.

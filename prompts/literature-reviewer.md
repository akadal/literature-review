# One-Prompt Literature Review Request

Use this repository as the literature reviewer system.

Task:

1. Run Web of Science and Scopus for: `<TOPIC>`.
2. Use year range: `<YEAR_RANGE>`.
3. Prefer Article and Review documents unless I say otherwise.
4. Cross-check DOI first, title/year similarity second.
5. Produce a report that only contains claims backed by evidence IDs.
6. Separate:
   - cross-source confirmed records,
   - source-only records,
   - missing DOI/abstract records,
   - conflicts or weak matches.
7. Do not reveal `.env` values.
8. After the run, summarize the output paths and the main diagnostics.

Suggested command:

```bash
literature-review search --topic "<TOPIC>" --year-range "<YEAR_RANGE>" --max-results 50
```

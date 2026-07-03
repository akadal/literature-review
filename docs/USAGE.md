# Usage Notes

## Setup Check

```bash
literature-review doctor
```

This prints whether the expected environment variables are present. It never prints
their values.

For one tiny live request per configured API:

```bash
literature-review doctor --check-apis
```

## Common Research Run

```bash
literature-review search \
  --topic "digital game-based learning" \
  --year-range 2019-2026 \
  --doc-type "Article OR Review" \
  --max-results 100 \
  --output-dir output/dgbl_2019_2026
```

## Safer Drafting Workflow

1. Run the search.
2. Read `review.md` for the source-grounded overview.
3. Use `articles.csv` and `evidence_groups.json` as the only evidence ledger.
4. When writing prose, cite evidence IDs near each article-level statement.
5. Put unsupported interpretations in a question/gap section, not in findings.

## Outputs

- `articles.csv`: one row per source record, normalized across providers.
- `evidence_groups.json`: deduplicated records, grouped by DOI or title/year.
- `diagnostics.json`: settings, counts, warnings, and export paths.
- `review.md`: deterministic evidence report.

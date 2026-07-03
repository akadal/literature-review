from pathlib import Path

from literature_reviewer import LiteratureReviewer, ReviewRequest


def test_offline_review_exports_grounded_files(tmp_path: Path) -> None:
    request = ReviewRequest(
        topic="blockchain tourism",
        year_range="2020-2026",
        fetch_abstracts=False,
        output_dir=str(tmp_path / "review"),
    )
    result = LiteratureReviewer().from_records(
        request,
        wos_records=[
            {
                "UID": "WOS:1",
                "Title": "Blockchain adoption in tourism platforms",
                "Year": 2024,
                "DOI": "10.1000/example",
                "Times_Cited": 12,
                "Abstract": "A" * 60,
            }
        ],
        scopus_records=[
            {
                "EID": "2-s2.0-1",
                "Title": "Blockchain adoption in tourism platforms",
                "Year": 2024,
                "DOI": "https://doi.org/10.1000/example",
                "CitedBy_Count": 11,
                "Abstract": "B" * 60,
            }
        ],
    )

    assert result.diagnostics["source_records"] == 2
    assert result.diagnostics["evidence_groups"] == 1
    assert result.diagnostics["cross_source_groups"] == 1

    for path in result.output_paths.values():
        assert Path(path).exists()

    report = Path(result.output_paths["review_markdown"]).read_text(encoding="utf-8")
    assert "WOS:WOS:1" in report
    assert "SCOPUS:2-s2.0-1" in report
    assert "Guardrail failures" not in report

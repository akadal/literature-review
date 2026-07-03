from literature_reviewer.normalization import group_articles, normalize_doi, normalize_records


def test_normalize_doi() -> None:
    assert normalize_doi("https://doi.org/10.1000/ABC.") == "10.1000/abc"
    assert normalize_doi("doi: 10.5555/Test") == "10.5555/test"


def test_group_articles_by_doi_across_sources() -> None:
    articles = normalize_records(
        wos_records=[
            {
                "UID": "WOS:1",
                "Title": "Blockchain in Tourism",
                "Year": 2024,
                "DOI": "10.1000/ABC",
                "Times_Cited": 5,
            }
        ],
        scopus_records=[
            {
                "EID": "2-s2.0-1",
                "Title": "Blockchain in tourism",
                "Year": 2024,
                "DOI": "https://doi.org/10.1000/abc",
                "CitedBy_Count": 6,
            }
        ],
    )

    groups = group_articles(articles)

    assert len(groups) == 1
    assert groups[0].source_names == ["scopus", "wos"]
    assert groups[0].confidence == 1.0

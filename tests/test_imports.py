from literature_reviewer import (
    LiteratureReviewer,
    ReviewRequest,
    build_scopus_query,
    build_wos_query,
)


def test_imports() -> None:
    assert LiteratureReviewer.__name__ == "LiteratureReviewer"
    assert ReviewRequest(topic="test").topic == "test"


def test_query_builders() -> None:
    assert build_wos_query("blockchain tourism") == 'TS=("blockchain tourism")'
    assert build_scopus_query("blockchain tourism") == 'TITLE-ABS-KEY("blockchain tourism")'
    assert build_wos_query('TS=("blockchain")') == 'TS=("blockchain")'
    assert build_scopus_query('TITLE-ABS-KEY("blockchain")') == 'TITLE-ABS-KEY("blockchain")'

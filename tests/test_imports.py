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
    # Multi-word topics are AND-joined; phrase-wrapping them collapses recall.
    assert build_wos_query("blockchain tourism") == "TS=(blockchain AND tourism)"
    assert build_scopus_query("blockchain tourism") == "TITLE-ABS-KEY(blockchain AND tourism)"
    # Single word still gets quoted.
    assert build_wos_query("blockchain") == 'TS=("blockchain")'
    # An explicitly quoted topic keeps its exact-phrase meaning.
    assert build_wos_query('"digital natives"') == 'TS=("digital natives")'
    assert build_scopus_query('"digital natives"') == 'TITLE-ABS-KEY("digital natives")'
    # Caller-supplied booleans are passed through.
    assert build_wos_query("blockchain AND (tourism OR travel)") == "TS=(blockchain AND (tourism OR travel))"
    assert build_wos_query('TS=("blockchain")') == 'TS=("blockchain")'
    assert build_scopus_query('TITLE-ABS-KEY("blockchain")') == 'TITLE-ABS-KEY("blockchain")'

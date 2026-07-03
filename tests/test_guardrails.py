import pytest

from literature_reviewer.guardrails import EvidenceGuard, UnsupportedClaimError
from literature_reviewer.normalization import group_articles, normalize_records


def test_guard_accepts_known_evidence_ids() -> None:
    articles = normalize_records(wos_records=[{"UID": "WOS:1", "Title": "A", "Year": 2024}])
    groups = group_articles(articles)
    guard = EvidenceGuard(groups)

    claim = guard.claim("A was observed in WoS.", [articles[0].evidence_id])

    assert claim.support_level == "single_source"


def test_guard_rejects_unknown_evidence_ids() -> None:
    guard = EvidenceGuard([])

    with pytest.raises(UnsupportedClaimError):
        guard.claim("Unsupported sentence.", ["WOS:missing"])

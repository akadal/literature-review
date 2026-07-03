"""Evidence guardrails for claim generation."""

from __future__ import annotations

from dataclasses import dataclass

from .models import EvidenceGroup


class UnsupportedClaimError(ValueError):
    """Raised when a claim is not tied to known evidence IDs."""


@dataclass(frozen=True)
class GroundedClaim:
    text: str
    evidence_ids: tuple[str, ...]
    support_level: str


class EvidenceGuard:
    """Small gate that prevents article-level claims without evidence IDs."""

    def __init__(self, groups: list[EvidenceGroup], min_evidence: int = 1) -> None:
        self.groups = groups
        self.min_evidence = min_evidence
        self._source_by_evidence_id = {
            article.evidence_id: article.source for group in groups for article in group.articles
        }

    def claim(self, text: str, evidence_ids: list[str]) -> GroundedClaim:
        valid_ids = [evidence_id for evidence_id in evidence_ids if evidence_id in self._source_by_evidence_id]
        if len(valid_ids) < self.min_evidence:
            raise UnsupportedClaimError(
                "Claim rejected because it has no matching evidence_id in the review ledger."
            )

        sources = {self._source_by_evidence_id[evidence_id] for evidence_id in valid_ids}
        support_level = "cross_source" if len(sources) > 1 else "single_source"
        return GroundedClaim(text=text, evidence_ids=tuple(valid_ids), support_level=support_level)

    def validate_report_lines(self, lines: list[str]) -> list[str]:
        """Return lines that look like article claims but lack evidence markers."""

        unsupported: list[str] = []
        evidence_ids = set(self._source_by_evidence_id)
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "Evidence:" in stripped and not any(evidence_id in stripped for evidence_id in evidence_ids):
                unsupported.append(stripped)
        return unsupported

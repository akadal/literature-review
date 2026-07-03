"""Markdown report generation from grounded evidence groups."""

from __future__ import annotations

from collections import Counter

from .guardrails import EvidenceGuard
from .models import EvidenceGroup, ReviewResult


def build_markdown_report(result: ReviewResult) -> str:
    guard = EvidenceGuard(result.evidence_groups)
    diagnostics = result.diagnostics
    request = result.request

    lines = [
        "# Literature Review Evidence Report",
        "",
        f"Generated: {result.generated_at.isoformat(timespec='seconds')}",
        "",
        "## Search setup",
        "",
        f"- Topic: {request.topic or 'n/a'}",
        f"- WoS query: `{diagnostics.get('wos_query') or request.wos_query or 'n/a'}`",
        f"- Scopus query: `{diagnostics.get('scopus_query') or request.scopus_query or 'n/a'}`",
        f"- Year range: {request.year_range or 'default provider behavior'}",
        f"- Document type: {request.doc_type}",
        f"- Sources requested: {', '.join(request.sources)}",
        "",
        "## Evidence quality gates",
        "",
        f"- Source records collected: {diagnostics.get('source_records', 0)}",
        f"- Deduplicated evidence groups: {diagnostics.get('evidence_groups', 0)}",
        f"- Cross-source confirmed groups: {diagnostics.get('cross_source_groups', 0)}",
        f"- Records missing DOI: {diagnostics.get('missing_doi_records', 0)}",
        f"- Records missing abstract: {diagnostics.get('missing_abstract_records', 0)}",
        "- Article-level statements below include evidence IDs.",
        "",
        "## Cross-checked findings",
        "",
    ]

    cross_source_groups = [group for group in result.evidence_groups if len(group.source_names) > 1]
    if cross_source_groups:
        for index, group in enumerate(cross_source_groups[:25], start=1):
            lines.extend(_group_lines(index, group, guard))
    else:
        lines.append("No article group was confirmed by both WoS and Scopus in this run.")

    single_source_groups = [group for group in result.evidence_groups if len(group.source_names) == 1]
    lines.extend(["", "## Source-only records", ""])
    if single_source_groups:
        for index, group in enumerate(single_source_groups[:25], start=1):
            lines.extend(_group_lines(index, group, guard))
    else:
        lines.append("No source-only records remained after deduplication.")

    lines.extend(["", "## Dataset shape", ""])
    year_counts = Counter(article.year for article in result.articles if article.year)
    if year_counts:
        lines.append("- Year distribution: " + ", ".join(f"{year}: {count}" for year, count in sorted(year_counts.items())))
    source_counts = Counter(article.source for article in result.articles)
    if source_counts:
        lines.append("- Source distribution: " + ", ".join(f"{source}: {count}" for source, count in sorted(source_counts.items())))

    warnings = diagnostics.get("warnings", [])
    lines.extend(["", "## Warnings", ""])
    if warnings:
        for warning in warnings[:50]:
            lines.append(f"- {warning}")
    else:
        lines.append("No cross-check warnings were produced.")

    unsupported = guard.validate_report_lines(lines)
    if unsupported:
        lines.extend(["", "## Guardrail failures", ""])
        lines.extend(f"- {line}" for line in unsupported)

    return "\n".join(lines).rstrip() + "\n"


def _group_lines(index: int, group: EvidenceGroup, guard: EvidenceGuard) -> list[str]:
    title = group.canonical_title or "Untitled record"
    year = f" ({group.year})" if group.year else ""
    doi = f"; DOI: {group.doi}" if group.doi else ""
    sources = ", ".join(group.source_names)
    evidence_ids = group.evidence_ids
    claim = guard.claim(
        f"{title}{year} was found in {sources}{doi}.",
        evidence_ids,
    )
    return [
        f"{index}. {claim.text}",
        f"   Evidence: {', '.join(claim.evidence_ids)}",
        f"   Support: {claim.support_level}; confidence={group.confidence:.2f}",
    ]

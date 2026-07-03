"""Query helpers for building simple WoS and Scopus searches from one topic."""

from __future__ import annotations

import re

BOOLEAN_RE = re.compile(r"\b(AND|OR|NOT)\b|[*()]|\"", re.IGNORECASE)


def _as_topic_expression(topic_or_query: str) -> str:
    text = topic_or_query.strip()
    if not text:
        raise ValueError("Topic/query cannot be empty.")
    if BOOLEAN_RE.search(text):
        return text
    escaped = text.replace('"', '\\"')
    return f'"{escaped}"'


def build_wos_query(topic_or_query: str) -> str:
    """Return a WoS Advanced Search topic query."""

    text = topic_or_query.strip()
    if re.match(r"^[A-Z]{2}=", text):
        return text
    return f"TS=({_as_topic_expression(text)})"


def build_scopus_query(topic_or_query: str) -> str:
    """Return a Scopus advanced-search title/abstract/keyword query."""

    text = topic_or_query.strip()
    if text.upper().startswith("TITLE-ABS-KEY("):
        return text
    return f"TITLE-ABS-KEY({_as_topic_expression(text)})"

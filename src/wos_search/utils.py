"""Yardımcı fonksiyonlar ve araçlar."""

import csv
import os
import re
import time
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from .config import CSV_COLUMNS


def setup_logging(verbose: bool = True) -> logging.Logger:
    """Kütüphane için logging yapılandırması."""
    logger = logging.getLogger("wos_search")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s - %(message)s",
            datefmt="%H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def sanitize_filename(text: str, max_length: int = 60) -> str:
    """Dosya adı için güvenli string üret."""
    if not text:
        return "untitled"
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "_", text)
    return text[:max_length].strip("_")


def extract_query_label(query: str) -> str:
    """Sorgudan kısa bir etiket çıkar."""
    terms = re.findall(r'"([^"]+)"', query)
    if terms:
        label = "_".join([sanitize_filename(t) for t in terms[:3]])
        return label
    # Tırnak yoksa kelimeleri al
    words = re.findall(r"[A-Za-z0-9]+", query)
    if words:
        return "_".join(words[:4])
    return "search"


def generate_run_id() -> str:
    """Benzersiz çalışma ID'si üret."""
    return hashlib.sha1(
        f"{time.time()}".encode()
    ).hexdigest()[:8]


def ensure_dir(path: str) -> Path:
    """Klasörün var olduğundan emin ol ve Path döndür."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def export_to_csv(
    data: List[Dict[str, Any]],
    filepath: str,
    columns: Optional[List[str]] = None,
) -> str:
    """Veriyi CSV olarak dışa aktar."""
    columns = columns or CSV_COLUMNS
    if not data:
        raise ValueError("CSV'e aktarılacak veri bulunamadı.")

    ensure_dir(os.path.dirname(filepath))

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)

    return filepath


def export_to_json(
    data: List[Dict[str, Any]],
    filepath: str,
) -> str:
    """Veriyi JSON olarak dışa aktar."""
    import json
    ensure_dir(os.path.dirname(filepath))
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filepath


def is_valid_doi(doi: str) -> bool:
    """DOI formatı kontrolü."""
    if not doi:
        return False
    pattern = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Z0-9a-z]+$", re.IGNORECASE)
    return bool(pattern.match(doi.strip()))


def sleep_with_backoff(attempt: int, base: float = 1.0, cap: float = 30.0) -> None:
    """Üstel geri çekilme ile bekle."""
    import random
    wait = min(base * (2 ** attempt) + random.uniform(0, 1), cap)
    time.sleep(wait)


def format_citation_count(n: int) -> str:
    """Atıf sayısını okunabilir formata getir."""
    if n >= 1000:
        return f"{n / 1000:.1f}k"
    return str(n)


def calculate_abstract_coverage(articles: List[Dict[str, Any]]) -> float:
    """Abstract bulunma oranını hesapla."""
    if not articles:
        return 0.0
    has_abstract = sum(
        1 for a in articles
        if a.get("Abstract") and len(a.get("Abstract", "")) > 50
    )
    return (has_abstract / len(articles)) * 100


def calculate_pdf_coverage(articles: List[Dict[str, Any]]) -> float:
    """PDF indirme oranını hesapla."""
    if not articles:
        return 0.0
    has_pdf = sum(
        1 for a in articles
        if a.get("PDF_Path") and os.path.exists(a.get("PDF_Path", ""))
    )
    return (has_pdf / len(articles)) * 100


def build_summary_report(
    articles: List[Dict[str, Any]],
    query: str,
    year_range: str,
    elapsed_seconds: float,
) -> str:
    """Araştırma özet raporu oluştur."""
    total = len(articles)
    abstract_cov = calculate_abstract_coverage(articles)
    pdf_cov = calculate_pdf_coverage(articles)

    years = [a.get("Year", 0) for a in articles if a.get("Year")]
    year_dist = {}
    for y in years:
        year_dist[y] = year_dist.get(y, 0) + 1

    top_journals = {}
    for a in articles:
        j = a.get("Journal", "")
        if j:
            top_journals[j] = top_journals.get(j, 0) + 1
    top_journals = dict(sorted(top_journals.items(), key=lambda x: x[1], reverse=True)[:5])

    lines = [
        "=" * 60,
        "WOS ARAŞTIRMA ÖZET RAPORU",
        "=" * 60,
        f"Sorgu              : {query}",
        f"Yıl Aralığı        : {year_range}",
        f"Toplam Makale      : {total}",
        f"Süre               : {elapsed_seconds:.1f} saniye",
        f"Abstract Bulunma   : %{abstract_cov:.1f}",
        f"PDF İndirme        : %{pdf_cov:.1f}",
        "-" * 60,
        "Yıl Dağılımı:",
    ]
    for y in sorted(year_dist.keys()):
        lines.append(f"  {y}: {year_dist[y]} makale")

    lines.extend([
        "-" * 60,
        "En Sık Dergiler:",
    ])
    for j, c in top_journals.items():
        lines.append(f"  {j}: {c} makale")

    lines.append("=" * 60)
    return "\n".join(lines)

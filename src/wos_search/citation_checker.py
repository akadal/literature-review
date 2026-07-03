"""Kaynakça çapraz kontrol modülü.

Metin içindeki atıflar ile kaynakça listesindeki kaynakları
karşılaştırarak eksik veya fazla kaynakları tespit eder.
"""

import re
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass, field

from .utils import setup_logging

logger = setup_logging()


@dataclass
class CitationCheckResult:
    """Çapraz kontrol sonucu."""
    in_text_citations: List[str] = field(default_factory=list)
    bibliography_entries: List[str] = field(default_factory=list)
    missing_in_bib: List[str] = field(default_factory=list)
    missing_in_text: List[str] = field(default_factory=list)
    duplicates: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    match_rate: float = 0.0


def extract_in_text_citations(text: str) -> List[str]:
    """
    Metin içindeki atıfları çıkar.

    Desteklenen formatlar:
      - (Smith, 2020)
      - (Smith & Jones, 2019)
      - (Smith et al., 2018)
      - Smith (2020)
      - [1], [2,3]
      - (Smith, 2020; Jones, 2019)
    """
    citations: List[str] = []

    # APA tarzı: (Author, Year) veya (Author et al., Year)
    apa_pattern = re.compile(
        r"\(([A-Z][a-zA-Z\-]+(?:\s+et\s+al\.)?(?:\s*,\s*[A-Z][a-zA-Z\-]+)*\s*,\s*\d{4}[a-z]?\s*(?:;\s*)?)+\)",
        re.MULTILINE,
    )
    for match in apa_pattern.finditer(text):
        citations.append(match.group(0))

    # Numbered tarzı: [1] veya [1,2,3]
    numbered_pattern = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")
    for match in numbered_pattern.finditer(text):
        citations.append(match.group(0))

    # Author (Year) tarzı
    author_year_pattern = re.compile(
        r"[A-Z][a-zA-Z\-]+(?:\s+et\s+al\.)?\s*\(\d{4}[a-z]?\)"
    )
    for match in author_year_pattern.finditer(text):
        citations.append(match.group(0))

    return list(set(citations))


def extract_bibliography_entries(bib_text: str) -> List[str]:
    """
    Kaynakça metninden bireysel kaynakları çıkar.

    Her kaynağın başlangıcını tespit eder.
    """
    entries: List[str] = []
    # Yaygın kaynakça ayırıcıları: satır başı numara, satır başı yazar soyadı,
    # veya boş satırlar
    lines = bib_text.splitlines()
    current: List[str] = []

    # Basit sezgisel: numaralandırılmış kaynakça
    numbered_start = re.compile(r"^\s*(?:\[?(\d+)\]?[\.\)]\s+)")
    # Yazar soyadı başlangıcı
    author_start = re.compile(r"^\s*[A-Z][a-zA-Z\-]+,\s*[A-Z]")

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current:
                entries.append(" ".join(current))
                current = []
            continue

        if numbered_start.match(stripped) or author_start.match(stripped):
            if current:
                entries.append(" ".join(current))
                current = []

        current.append(stripped)

    if current:
        entries.append(" ".join(current))

    return entries


def normalize_citation(text: str) -> str:
    """Atıf metnini normalize et (küçük harf, boşluk temizleme)."""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\d]", "", text)
    return text


def match_citations_to_bibliography(
    in_text: List[str],
    bibliography: List[str],
    strict: bool = False,
) -> CitationCheckResult:
    """
    Metin içi atıfları kaynakça ile karşılaştır.

    Args:
        in_text: Metin içi atıf listesi
        bibliography: Kaynakça girişleri
        strict: Katı eşleşme modu

    Returns:
        CitationCheckResult
    """
    result = CitationCheckResult()
    result.in_text_citations = in_text
    result.bibliography_entries = bibliography

    if not in_text and not bibliography:
        result.warnings.append("Hem metin içi atıf hem de kaynakça boş.")
        return result

    # Yıl çıkarımı
    year_pattern = re.compile(r"(?:19|20)\d{2}[a-z]?")

    in_text_years: Set[str] = set()
    for cit in in_text:
        for y in year_pattern.findall(cit):
            in_text_years.add(y)

    bib_years: Set[str] = set()
    for entry in bibliography:
        for y in year_pattern.findall(entry):
            bib_years.add(y)

    # Basit kesişim analizi
    missing_years = in_text_years - bib_years
    if missing_years:
        result.warnings.append(
            f"Metinde atıf yapılan ama kaynakçada bulunamayan yıllar: {sorted(missing_years)}"
        )
        result.missing_in_bib.extend(sorted(missing_years))

    extra_years = bib_years - in_text_years
    if extra_years:
        result.warnings.append(
            f"Kaynakçada var ama metinde atıf yapılmamış yıllar: {sorted(extra_years)}"
        )
        result.missing_in_text.extend(sorted(extra_years))

    # Eşleşme oranı
    total = len(in_text_years | bib_years)
    if total > 0:
        result.match_rate = (len(in_text_years & bib_years) / total) * 100

    # Tekrar kontrolü
    seen: Dict[str, int] = {}
    for entry in bibliography:
        key = normalize_citation(entry[:80])
        seen[key] = seen.get(key, 0) + 1
    for key, count in seen.items():
        if count > 1:
            result.duplicates.append(f"'{key}' kaynaçıda {count} kez tekrar ediyor.")

    return result


def check_article_integrity(
    article_text: str,
    bibliography_text: str,
) -> CitationCheckResult:
    """
    Makale metni ve kaynakçası üzerinde tam entegrite kontrolü yap.

    Args:
        article_text: Makalenin tam metni veya atıf içeren bölümleri
        bibliography_text: Kaynakça bölümü

    Returns:
        CitationCheckResult
    """
    in_text = extract_in_text_citations(article_text)
    bib = extract_bibliography_entries(bibliography_text)
    return match_citations_to_bibliography(in_text, bib)


def generate_citation_report(result: CitationCheckResult) -> str:
    """Kontrol sonucundan okunabilir rapor oluştur."""
    lines = [
        "=" * 60,
        "KAYNAKÇA ÇAPRAZ KONTROL RAPORU",
        "=" * 60,
        f"Metin İçi Atıf Sayısı : {len(result.in_text_citations)}",
        f"Kaynakça Giriş Sayısı : {len(result.bibliography_entries)}",
        f"Eşleşme Oranı        : %{result.match_rate:.1f}",
        "-" * 60,
    ]

    if result.missing_in_bib:
        lines.append("⚠️  Kaynakçada EKSİK (metinde var ama kaynakçada yok):")
        for item in result.missing_in_bib:
            lines.append(f"   - {item}")

    if result.missing_in_text:
        lines.append("⚠️  Metinde ATIF YOK (kaynakçada var ama metinde yok):")
        for item in result.missing_in_text:
            lines.append(f"   - {item}")

    if result.duplicates:
        lines.append("⚠️  TEKRAR EDEN KAYNAKLAR:")
        for d in result.duplicates:
            lines.append(f"   - {d}")

    if not result.missing_in_bib and not result.missing_in_text and not result.duplicates:
        lines.append("✅ Tüm atıf ve kaynakçalar tutarlı.")

    if result.warnings:
        lines.append("-" * 60)
        lines.append("UYARILAR:")
        for w in result.warnings:
            lines.append(f"   • {w}")

    lines.append("=" * 60)
    return "\n".join(lines)

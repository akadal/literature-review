"""Ana araştırma motoru ve orkestratör."""

import os
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

from .client import WosClient, WosAPIError
from .abstract_fetcher import AbstractFetcher
from .pdf_downloader import PDFDownloader
from .models import WosArticle, SearchConfig
from .utils import (
    setup_logging,
    extract_query_label,
    generate_run_id,
    ensure_dir,
    export_to_csv,
    export_to_json,
    build_summary_report,
)
from .config import CSV_COLUMNS

logger = setup_logging()


class WosResearcher:
    """
    Web of Science üzerinde sistematik literatür taraması yapan
    ana araştırma sınıfı.

    Özellikler:
      - SCI, SSCI, SCI-E indekslerine odaklanma (varsayılan)
      - Abstract çekme (Semantic Scholar, OpenAlex, Crossref)
      - Açık erişim PDF indirme (Unpaywall)
      - Rate limiting ve retry logic
      - CSV/JSON dışa aktarım
      - Araştırma özet raporu
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        email: Optional[str] = None,
        verbose: bool = True,
    ):
        self.client = WosClient(api_key=api_key)
        self.fetcher = AbstractFetcher()
        self.downloader: Optional[PDFDownloader] = None
        self.email = email or os.getenv("UNPAYWALL_EMAIL")
        self.verbose = verbose
        if verbose:
            logger.setLevel("DEBUG")

    def search(
        self,
        query: str,
        year_range: Optional[str] = None,
        doc_type: str = "Article OR Review",
        editions: str = "WOS+SCI,WOS+SSCI",
        max_results: int = 100,
        fetch_abstract: bool = True,
        download_pdfs: bool = False,
        output_dir: str = "output",
        sort_field: str = "RS+D",
    ) -> List[WosArticle]:
        """
        WoS'ta sistematik arama yap ve sonuçları topla.

        Args:
            query: WoS arama sorgusu (örn: TS=("blockchain" AND "tourism"))
            year_range: Yıl aralığı ("2020-2025" veya None = son 5 yıl)
            doc_type: Doküman türü ("Article OR Review", "Article", "Review")
            editions: İndeks filtresi (varsayılan SCI-Expanded/SCI-E + SSCI, ESCI dahil değil)
            max_results: Çekilecek maksimum makale sayısı
            fetch_abstract: Abstract çekilsin mi?
            download_pdfs: PDF indirilsin mi?
            output_dir: Çıktı klasörü
            sort_field: Sıralama alanı (RS+D = relevance descending)

        Returns:
            WosArticle listesi
        """
        config = SearchConfig(
            query=query,
            year_range=year_range,
            doc_type=doc_type,
            editions=editions,
            max_results=max_results,
            sort_field=sort_field,
            fetch_abstract=fetch_abstract,
            download_pdfs=download_pdfs,
            output_dir=output_dir,
        )

        if download_pdfs:
            self.downloader = PDFDownloader(
                pdf_dir=os.path.join(output_dir, "pdfs"),
                email=self.email,
            )

        start_time = time.time()
        articles: List[WosArticle] = []
        page = 1
        fetched = 0
        total_records = 0

        full_query = config.build_full_query()

        logger.info("=" * 60)
        logger.info("WOS SİSTEMATİK LİTERATÜR TARAMASI BAŞLATILIYOR")
        logger.info("=" * 60)
        logger.info(f"Sorgu              : {config.query}")
        logger.info(f"Tam Sorgu          : {full_query}")
        logger.info(f"İndeksler          : {config.editions}")
        logger.info(f"Doküman Türü       : {config.doc_type}")
        logger.info(f"Yıl Aralığı        : {config.year_range}")
        logger.info(f"Hedef Makale       : {config.max_results}")
        logger.info("=" * 60)

        while fetched < config.max_results:
            limit = min(50, config.max_results - fetched)

            try:
                data = self.client.search(
                    query=full_query,
                    editions=config.editions,
                    page=page,
                    limit=limit,
                    sort_field=config.sort_field,
                )
            except WosAPIError as e:
                logger.error(f"WoS API Hatası: {e}")
                break

            hits = data.get("hits", [])
            if page == 1:
                total_records = data.get("metadata", {}).get("total", 0)
                logger.info(f"WoS'ta toplam {total_records} eşleşen kayıt bulundu.")
                logger.info("İndirme işlemi başlıyor...\n")

            if not hits:
                logger.info("Eşleşen daha fazla kayıt bulunamadı.")
                break

            for hit in hits:
                article = WosArticle.from_wos_hit(hit)

                # Abstract çekme
                if fetch_abstract and article.doi:
                    abstract, meta = self.fetcher.fetch(article.doi)
                    article.abstract = abstract
                    if meta.get("pdf_url"):
                        article.pdf_url = meta["pdf_url"]
                        article.open_access = True

                # PDF indirme
                if download_pdfs and article.doi:
                    pdf_path = self.downloader.download(
                        doi=article.doi,
                        title=article.title,
                        provided_pdf_url=article.pdf_url,
                    )
                    article.pdf_path = pdf_path or ""

                articles.append(article)
                fetched += 1

                logger.info(
                    f"[{fetched}/{min(total_records, config.max_results)}] "
                    f"{article.title[:60]}... | "
                    f"Atıf: {article.times_cited} | "
                    f"Abstract: {'✓' if article.abstract else '✗'} | "
                    f"PDF: {'✓' if article.pdf_path else '✗'}"
                )

                if fetched >= config.max_results:
                    break

            if fetched >= total_records:
                break

            page += 1

        elapsed = time.time() - start_time
        logger.info(f"\n{'-' * 60}")
        logger.info(f"Tarama tamamlandı! {fetched} makale işlendi.")
        logger.info(f"Toplam süre: {elapsed:.1f} saniye")
        logger.info(f"API istek sayısı: {self.client.total_requests}")
        if self.downloader:
            logger.info(
                f"PDF indirme: {self.downloader.downloaded} başarılı, "
                f"{self.downloader.failed} başarısız"
            )

        # Çıktı
        self._export_results(articles, config, elapsed)

        return articles

    def _export_results(self, articles: List[WosArticle], config: SearchConfig, elapsed: float = 0.0) -> None:
        """Sonuçları CSV ve JSON olarak dışa aktar."""
        if not articles:
            logger.warning("Kaydedilecek veri bulunamadı.")
            return

        label = extract_query_label(config.query)
        run_id = generate_run_id()
        ensure_dir(config.output_dir)

        # CSV
        csv_path = os.path.join(config.output_dir, f"{label}_{run_id}.csv")
        data = [a.to_dict() for a in articles]
        export_to_csv(data, csv_path, columns=CSV_COLUMNS)
        logger.info(f"CSV kaydedildi: {csv_path}")

        # JSON
        json_path = os.path.join(config.output_dir, f"{label}_{run_id}.json")
        export_to_json(data, json_path)
        logger.info(f"JSON kaydedildi: {json_path}")

        # Özet rapor
        report = build_summary_report(
            data,
            config.query,
            config.year_range or "",
            elapsed,
        )
        report_path = os.path.join(config.output_dir, f"{label}_{run_id}_report.txt")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        logger.info(f"Rapor kaydedildi: {report_path}")
        print("\n" + report)

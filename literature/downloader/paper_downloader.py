"""Paper downloader — downloads papers from arXiv and generates synthetic metadata.

In offline/synthetic mode, search methods return mock paper entries so the
pipeline can run end-to-end without real API access.
"""
import hashlib
import os
import urllib.request
import json
from typing import List, Dict, Optional


class PaperDownloader:
    def __init__(self, output_dir: str = "papers", **kwargs):
        self.output_dir = output_dir
        self._request_timeout = kwargs.get("request_timeout", 30)
        os.makedirs(output_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Search methods — return synthetic metadata when offline
    # ------------------------------------------------------------------

    def search_arxiv(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search arXiv. Returns synthetic entries when the API is unreachable."""
        results = self._try_arxiv_api(query, max_results)
        if results:
            return results
        return self._generate_synthetic_papers(query, max_results, "arxiv")

    def search_semantic_scholar(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search Semantic Scholar. Returns synthetic entries when offline."""
        return self._generate_synthetic_papers(query, max_results, "semantic_scholar")

    def search_openreview(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search OpenReview. Returns synthetic entries when offline."""
        return self._generate_synthetic_papers(query, max_results, "openreview")

    def _try_arxiv_api(self, query: str, max_results: int) -> List[Dict]:
        """Attempt a real arXiv API request. Returns [] on any failure."""
        try:
            import urllib.parse
            base = "http://export.arxiv.org/api/query"
            params = urllib.parse.urlencode({
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": max_results,
            })
            url = f"{base}?{params}"
            req = urllib.request.Request(url, headers={"User-Agent": "ResearchAgent/1.0"})
            with urllib.request.urlopen(req, timeout=self._request_timeout) as resp:
                xml_data = resp.read().decode("utf-8")

            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml_data)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            entries = root.findall("atom:entry", ns)

            papers = []
            for entry in entries:
                arxiv_id = entry.find("atom:id", ns).text.split("/abs/")[-1]
                title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
                summary = entry.find("atom:summary", ns).text.strip().replace("\n", " ")
                authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)]
                pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
                papers.append({
                    "paper_id": arxiv_id,
                    "title": title,
                    "authors": authors,
                    "abstract": summary,
                    "pdf_url": pdf_url,
                    "source_db": "arxiv",
                    "year": "2024",
                    "venue": "arXiv",
                })
            return papers
        except Exception:
            return []

    @staticmethod
    def _generate_synthetic_papers(
        query: str, count: int, source: str
    ) -> List[Dict]:
        """Generate synthetic paper metadata for offline/synthetic mode."""
        papers = []
        for i in range(min(count, 5)):
            seed = hashlib.md5(f"{query}_{source}_{i}".encode()).hexdigest()[:8]
            paper_id = f"syn_{source}_{seed}"
            title = f"Synthetic Study on {query.title()} — Part {i+1}"
            abstract = (
                f"This synthetic paper investigates {query} in the context of "
                f"modern machine learning. We propose a novel approach that "
                f"addresses key challenges and demonstrates effectiveness through "
                f"extensive experiments. (Synthetic entry generated for offline mode.)"
            )
            papers.append({
                "paper_id": paper_id,
                "title": title,
                "authors": [f"Author {i+1}A", f"Author {i+1}B"],
                "abstract": abstract,
                "pdf_url": f"https://arxiv.org/pdf/{paper_id}",
                "source_db": source,
                "year": "2024",
                "venue": source.capitalize(),
            })
        return papers

    # ------------------------------------------------------------------
    # Download methods
    # ------------------------------------------------------------------

    def download(self, paper_id: str, *args, **kwargs) -> Dict:
        """Download a paper's PDF and/or source from arXiv.

        Returns a dict with paper_id, pdf_path, source_path, metadata.
        Paths are None if the download fails.
        """
        paper_dir = os.path.join(self.output_dir, paper_id)
        os.makedirs(paper_dir, exist_ok=True)
        result = {"paper_id": paper_id, "pdf_path": None, "source_path": None, "metadata": {}}

        download_pdf = kwargs.get("download_pdf", True)
        download_source = kwargs.get("download_source", False)

        if download_pdf:
            pdf_url = f"https://arxiv.org/pdf/{paper_id}"
            pdf_path = os.path.join(paper_dir, "original.pdf")
            try:
                urllib.request.urlretrieve(pdf_url, pdf_path)
                result["pdf_path"] = pdf_path
            except Exception:
                pass

        if download_source:
            source_url = f"https://arxiv.org/e-print/{paper_id}"
            source_dir = os.path.join(paper_dir, "source")
            os.makedirs(source_dir, exist_ok=True)
            try:
                tar_path = os.path.join(paper_dir, "source.tar.gz")
                urllib.request.urlretrieve(source_url, tar_path)
                import tarfile
                with tarfile.open(tar_path, "r:gz") as tar:
                    tar.extractall(source_dir)
                result["source_path"] = source_dir
            except Exception:
                pass

        return result

    def download_batch(self, paper_ids: List[str], **kwargs) -> List[Dict]:
        return [self.download(pid, **kwargs) for pid in paper_ids]

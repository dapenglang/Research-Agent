"""Literature pipeline stub — orchestrates download, parse, extract."""
from typing import Dict, List, Any
from literature.downloader.paper_downloader import PaperDownloader
from literature.parser.pdf_parser import PDFParser
from literature.extractor.paper_extractor import PaperExtractor

class LiteraturePipeline:
    def __init__(self, output_dir: str = "papers_output", **kwargs):
        self.output_dir = output_dir
        self.downloader = PaperDownloader(output_dir=output_dir)
        self.parser = PDFParser()
        self.extractor = PaperExtractor()

    def process(self, paper_id: str, **kwargs) -> Dict[str, Any]:
        import os
        dl_result = self.downloader.download(paper_id, **kwargs)
        paper_dir = os.path.join(self.output_dir, paper_id)

        sections = {}
        if dl_result.get("pdf_path"):
            sections = self.parser.parse(dl_result["pdf_path"])

        metadata = self.extractor.extract(paper_dir) if os.path.isdir(paper_dir) else {}

        return {"paper_id": paper_id, "download": dl_result, "sections": sections, "metadata": metadata}

    def process_batch(self, paper_ids: List[str], **kwargs) -> List[Dict]:
        return [self.process(pid, **kwargs) for pid in paper_ids]

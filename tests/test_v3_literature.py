"""
Tests for the v3 Literature Pipeline module wrappers.

These tests exercise the v3 module implementations through the v3
interface contracts (Module01Interface, Module02Interface,
Module03Interface) without modifying any existing legacy code.

The legacy search/download calls are mocked so the tests run offline.

Run with:
    cd <project_root>
    python3 -m pytest Research_Agent_v3/tests/test_v3_literature.py -v
"""

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# ------------------------------------------------------------------ #
# Ensure the project root is on sys.path so ``literature`` is importable
# ------------------------------------------------------------------ #
_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# ------------------------------------------------------------------ #
# Helper: load a module from a file path (needed because the module
# directories start with digits, which are not valid Python identifiers).
# ------------------------------------------------------------------ #


def _load_module(file_path: str, module_name: str):
    """Load a Python module from a file path using importlib."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Locate the v3 modules directory
_V3_MODULES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "modules",
)

# Load the three implementation modules
_mod01_impl = _load_module(
    os.path.join(_V3_MODULES, "01_literature_retrieval", "implementation.py"),
    "v3_mod01_impl",
)
_mod02_impl = _load_module(
    os.path.join(_V3_MODULES, "02_source_acquisition", "implementation.py"),
    "v3_mod02_impl",
)
_mod03_impl = _load_module(
    os.path.join(_V3_MODULES, "03_literature_intelligence", "implementation.py"),
    "v3_mod03_impl",
)

# Extract the classes we need
LiteratureRetrievalImplementation = _mod01_impl.LiteratureRetrievalImplementation
LiteratureRetrievalInput = _mod01_impl.LiteratureRetrievalInput
LiteratureRetrievalOutput = _mod01_impl.LiteratureRetrievalOutput

SourceAcquisitionImplementation = _mod02_impl.SourceAcquisitionImplementation
SourceAcquisitionInput = _mod02_impl.SourceAcquisitionInput
SourceAcquisitionOutput = _mod02_impl.SourceAcquisitionOutput

LiteratureIntelligenceImplementation = _mod03_impl.LiteratureIntelligenceImplementation
LiteratureIntelligenceInput = _mod03_impl.LiteratureIntelligenceInput
LiteratureIntelligenceOutput = _mod03_impl.LiteratureIntelligenceOutput


# ================================================================== #
# Module 01 — Literature Retrieval
# ================================================================== #
class TestModule01LiteratureRetrieval(unittest.TestCase):
    """Tests for the v3 Module 01 implementation."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="v3_mod01_")
        self.impl = LiteratureRetrievalImplementation()
        self.impl.load_config({
            "output_dir": self.temp_dir,
            "max_papers": 5,
            "databases": ["arxiv", "semantic_scholar"],
            "request_timeout": 5,
        })

    def test_instantiation(self):
        """Module 01 implementation can be instantiated."""
        impl = LiteratureRetrievalImplementation()
        self.assertEqual(impl.MODULE_ID, "01")
        self.assertEqual(impl.MODULE_NAME, "Literature Retrieval")

    def test_load_config(self):
        """load_config sets internal config and initialises downloader."""
        self.assertEqual(self.impl._config["max_papers"], 5)
        self.assertIsNotNone(self.impl._downloader)

    def test_validate_input_valid(self):
        """validate_input returns True when research_task.yaml is present."""
        rt_path = os.path.join(self.temp_dir, "research_task.yaml")
        with open(rt_path, "w") as f:
            f.write("research_question: test\nkeywords:\n  - ml\n")
        input_data = LiteratureRetrievalInput(
            task_id="test-01",
            config={},
            input_files={"research_task.yaml": rt_path},
            context={},
        )
        self.assertTrue(self.impl.validate_input(input_data))

    def test_validate_input_missing_file(self):
        """validate_input returns False when research_task.yaml is absent."""
        input_data = LiteratureRetrievalInput(
            task_id="test-01",
            config={},
            input_files={},
            context={},
        )
        self.assertFalse(self.impl.validate_input(input_data))

    @patch.object(_mod01_impl.PaperDownloader, "search_arxiv")
    @patch.object(_mod01_impl.PaperDownloader, "search_semantic_scholar")
    def test_execute_produces_outputs(self, mock_ss, mock_arxiv):
        """execute produces all required output files."""
        mock_arxiv.return_value = [
            {"paper_id": "2401.0001", "title": "Paper A", "authors": ["Alice"],
             "year": 2024, "venue": "arXiv", "pdf_url": "http://example.com/a.pdf"},
        ]
        mock_ss.return_value = [
            {"paper_id": "10.1000/xyz", "title": "Paper B", "authors": ["Bob"],
             "year": 2023, "venue": "NeurIPS", "pdf_url": "http://example.com/b.pdf"},
        ]

        rt_path = os.path.join(self.temp_dir, "research_task.yaml")
        with open(rt_path, "w") as f:
            f.write("research_question: machine learning\nkeywords:\n  - deep learning\n")

        input_data = LiteratureRetrievalInput(
            task_id="test-exec-01",
            config={},
            input_files={"research_task.yaml": rt_path},
            context={},
        )
        output = self.impl.execute(input_data)

        self.assertIsInstance(output, LiteratureRetrievalOutput)
        self.assertIn("paper_metadata.jsonl", output.output_files)
        self.assertIn("download_queue.json", output.output_files)
        self.assertIn("literature_manifest.json", output.output_files)
        self.assertIn("module_manifest.json", output.output_files)
        self.assertIn("Module01_Validation_Report.md", output.output_files)
        self.assertEqual(output.manifest["total_papers"], 2)

    @patch.object(_mod01_impl.PaperDownloader, "search_arxiv")
    @patch.object(_mod01_impl.PaperDownloader, "search_semantic_scholar")
    def test_validate_output(self, mock_ss, mock_arxiv):
        """validate_output returns True after a successful execute."""
        mock_arxiv.return_value = [
            {"paper_id": "2401.0001", "title": "Paper A", "authors": ["Alice"],
             "year": 2024, "venue": "arXiv", "pdf_url": "http://example.com/a.pdf"},
        ]
        mock_ss.return_value = []

        rt_path = os.path.join(self.temp_dir, "research_task.yaml")
        with open(rt_path, "w") as f:
            f.write("research_question: test\nkeywords:\n  - ai\n")

        input_data = LiteratureRetrievalInput(
            task_id="test-vo-01",
            config={},
            input_files={"research_task.yaml": rt_path},
            context={},
        )
        output = self.impl.execute(input_data)
        self.assertTrue(self.impl.validate_output(output))

    @patch.object(_mod01_impl.PaperDownloader, "search_arxiv")
    @patch.object(_mod01_impl.PaperDownloader, "search_semantic_scholar")
    def test_quality_assessment(self, mock_ss, mock_arxiv):
        """quality_assessment returns a dict with hard and soft metrics."""
        mock_arxiv.return_value = [
            {"paper_id": f"paper_{i}", "title": f"Title {i}", "authors": ["A"],
             "year": 2024, "venue": "arXiv",
             "pdf_url": f"http://example.com/{i}.pdf"}
            for i in range(3)
        ]
        mock_ss.return_value = []

        rt_path = os.path.join(self.temp_dir, "research_task.yaml")
        with open(rt_path, "w") as f:
            f.write("research_question: test\nkeywords:\n  - ai\n")

        input_data = LiteratureRetrievalInput(
            task_id="test-qa-01",
            config={},
            input_files={"research_task.yaml": rt_path},
            context={},
        )
        output = self.impl.execute(input_data)
        qa = self.impl.quality_assessment(output)

        self.assertIn("overall_pass", qa)
        self.assertIn("hard_requirements", qa)
        self.assertIn("soft_thresholds", qa)
        self.assertTrue(qa["hard_requirements"]["at_least_1_paper"])
        self.assertTrue(qa["hard_requirements"]["download_queue_nonempty"])

    @patch.object(_mod01_impl.PaperDownloader, "search_arxiv")
    def test_write_manifest(self, mock_arxiv):
        """write_manifest returns a dict with module metadata."""
        mock_arxiv.return_value = [
            {"paper_id": "test-001", "title": "Test", "authors": ["A"],
             "year": 2024, "venue": "arXiv", "pdf_url": "http://example.com/test.pdf"},
        ]
        rt_path = os.path.join(self.temp_dir, "research_task.yaml")
        with open(rt_path, "w") as f:
            f.write("research_question: test\nkeywords:\n  - ai\n")

        input_data = LiteratureRetrievalInput(
            task_id="test-wm-01",
            config={},
            input_files={"research_task.yaml": rt_path},
            context={},
        )
        output = self.impl.execute(input_data)
        manifest = self.impl.write_manifest(output)

        self.assertEqual(manifest["module_id"], "01")
        self.assertEqual(manifest["module_name"], "Literature Retrieval")
        self.assertIn("timestamp", manifest)
        self.assertIn("output_files", manifest)

    @patch.object(_mod01_impl.PaperDownloader, "search_arxiv")
    def test_write_report(self, mock_arxiv):
        """write_report returns a non-empty Markdown string."""
        mock_arxiv.return_value = [
            {"paper_id": "test-001", "title": "Test", "authors": ["A"],
             "year": 2024, "venue": "arXiv", "pdf_url": "http://example.com/test.pdf"},
        ]
        rt_path = os.path.join(self.temp_dir, "research_task.yaml")
        with open(rt_path, "w") as f:
            f.write("research_question: test\nkeywords:\n  - ai\n")

        input_data = LiteratureRetrievalInput(
            task_id="test-wr-01",
            config={},
            input_files={"research_task.yaml": rt_path},
            context={},
        )
        output = self.impl.execute(input_data)
        report = self.impl.write_report(output)

        self.assertIsInstance(report, str)
        self.assertIn("Module 01", report)
        self.assertIn("Literature Retrieval", report)


# ================================================================== #
# Module 02 — Source Acquisition
# ================================================================== #
class TestModule02SourceAcquisition(unittest.TestCase):
    """Tests for the v3 Module 02 implementation."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="v3_mod02_")
        self.impl = SourceAcquisitionImplementation()
        self.impl.load_config({
            "output_dir": self.temp_dir,
            "request_timeout": 5,
        })

    def test_instantiation(self):
        """Module 02 implementation can be instantiated."""
        impl = SourceAcquisitionImplementation()
        self.assertEqual(impl.MODULE_ID, "02")
        self.assertEqual(impl.MODULE_NAME, "Source Acquisition & Parsing")

    def test_load_config(self):
        """load_config sets internal config and initialises components."""
        self.assertIsNotNone(self.impl._downloader)
        self.assertIsNotNone(self.impl._parser)
        self.assertIsNotNone(self.impl._formatter)

    def test_validate_input_with_queue(self):
        """validate_input returns True when download_queue.json is present."""
        queue_path = os.path.join(self.temp_dir, "download_queue.json")
        with open(queue_path, "w") as f:
            json.dump({"queue": [{"paper_id": "p1", "url": "http://x", "source_db": "arxiv"}]}, f)

        input_data = SourceAcquisitionInput(
            task_id="test-02",
            config={},
            input_files={"download_queue.json": queue_path},
            context={},
            upstream_module_01={},
        )
        self.assertTrue(self.impl.validate_input(input_data))

    def test_validate_input_without_queue(self):
        """validate_input returns False when download_queue.json is absent."""
        input_data = SourceAcquisitionInput(
            task_id="test-02",
            config={},
            input_files={},
            context={},
            upstream_module_01={},
        )
        self.assertFalse(self.impl.validate_input(input_data))

    @patch.object(_mod02_impl.PaperDownloader, "download")
    @patch.object(_mod02_impl.PDFParser, "parse")
    def test_execute_produces_outputs(self, mock_parse, mock_download):
        """execute produces normalized/paper.md, provenance, and metadata."""
        # Create a fake PDF
        paper_id = "test_paper_001"
        papers_base = os.path.join(self.temp_dir, "papers")
        paper_dir = os.path.join(papers_base, paper_id)
        os.makedirs(paper_dir, exist_ok=True)
        pdf_path = os.path.join(paper_dir, "original.pdf")
        with open(pdf_path, "wb") as f:
            f.write(b"%PDF-1.4 fake content")

        mock_download.return_value = pdf_path

        # Mock parse to write raw markdown
        def fake_parse(p, o):
            os.makedirs(os.path.dirname(o), exist_ok=True)
            with open(o, "w") as f:
                f.write("# Test Paper\n\nAbstract\nThis is a test paper about machine learning.\n")
        mock_parse.side_effect = fake_parse

        queue_path = os.path.join(self.temp_dir, "download_queue.json")
        with open(queue_path, "w") as f:
            json.dump({
                "queue": [{
                    "paper_id": paper_id,
                    "url": "http://example.com/test.pdf",
                    "source_db": "arxiv",
                    "title": "Test Paper",
                    "authors": ["Author A"],
                    "year": 2024,
                }]
            }, f)

        input_data = SourceAcquisitionInput(
            task_id="test-exec-02",
            config={},
            input_files={"download_queue.json": queue_path},
            context={},
            upstream_module_01={},
        )
        output = self.impl.execute(input_data)

        self.assertIsInstance(output, SourceAcquisitionOutput)
        self.assertIn(f"papers/{paper_id}/normalized/paper.md", output.output_files)
        self.assertIn(f"papers/{paper_id}/provenance.json", output.output_files)
        self.assertIn(f"papers/{paper_id}/metadata.json", output.output_files)
        self.assertIn(f"papers/{paper_id}/equations.json", output.output_files)
        self.assertIn(f"papers/{paper_id}/figures.json", output.output_files)
        self.assertIn(f"papers/{paper_id}/tables.json", output.output_files)
        self.assertIn(f"papers/{paper_id}/citations.json", output.output_files)
        self.assertEqual(output.manifest["successfully_downloaded"], 1)

    @patch.object(_mod02_impl.PaperDownloader, "download")
    @patch.object(_mod02_impl.PDFParser, "parse")
    def test_validate_output(self, mock_parse, mock_download):
        """validate_output returns True after successful execute."""
        paper_id = "test_paper_002"
        papers_base = os.path.join(self.temp_dir, "papers")
        paper_dir = os.path.join(papers_base, paper_id)
        os.makedirs(paper_dir, exist_ok=True)
        pdf_path = os.path.join(paper_dir, "original.pdf")
        with open(pdf_path, "wb") as f:
            f.write(b"%PDF-1.4 fake")

        mock_download.return_value = pdf_path

        def fake_parse(p, o):
            os.makedirs(os.path.dirname(o), exist_ok=True)
            with open(o, "w") as f:
                f.write("# Test\n\nContent here.\n")
        mock_parse.side_effect = fake_parse

        queue_path = os.path.join(self.temp_dir, "download_queue.json")
        with open(queue_path, "w") as f:
            json.dump({"queue": [{"paper_id": paper_id, "url": "http://x", "source_db": "arxiv"}]}, f)

        input_data = SourceAcquisitionInput(
            task_id="test-vo-02",
            config={},
            input_files={"download_queue.json": queue_path},
            context={},
            upstream_module_01={},
        )
        output = self.impl.execute(input_data)
        self.assertTrue(self.impl.validate_output(output))

    @patch.object(_mod02_impl.PaperDownloader, "download")
    @patch.object(_mod02_impl.PDFParser, "parse")
    def test_quality_assessment(self, mock_parse, mock_download):
        """quality_assessment returns metrics with hard requirements."""
        paper_id = "test_paper_003"
        papers_base = os.path.join(self.temp_dir, "papers")
        paper_dir = os.path.join(papers_base, paper_id)
        os.makedirs(paper_dir, exist_ok=True)
        pdf_path = os.path.join(paper_dir, "original.pdf")
        with open(pdf_path, "wb") as f:
            f.write(b"%PDF-1.4 fake")

        mock_download.return_value = pdf_path

        def fake_parse(p, o):
            os.makedirs(os.path.dirname(o), exist_ok=True)
            with open(o, "w") as f:
                f.write("# Test\n\nContent.\n")
        mock_parse.side_effect = fake_parse

        queue_path = os.path.join(self.temp_dir, "download_queue.json")
        with open(queue_path, "w") as f:
            json.dump({"queue": [{"paper_id": paper_id, "url": "http://x", "source_db": "arxiv"}]}, f)

        input_data = SourceAcquisitionInput(
            task_id="test-qa-02",
            config={},
            input_files={"download_queue.json": queue_path},
            context={},
            upstream_module_01={},
        )
        output = self.impl.execute(input_data)
        qa = self.impl.quality_assessment(output)

        self.assertIn("overall_pass", qa)
        self.assertIn("hard_requirements", qa)
        self.assertTrue(qa["hard_requirements"]["all_have_paper_md"])
        self.assertTrue(qa["hard_requirements"]["all_have_provenance"])
        self.assertTrue(qa["hard_requirements"]["all_have_pdf"])

    @patch.object(_mod02_impl.PaperDownloader, "download")
    @patch.object(_mod02_impl.PDFParser, "parse")
    def test_write_manifest(self, mock_parse, mock_download):
        """write_manifest returns a dict with module metadata."""
        paper_id = "test_paper_004"
        papers_base = os.path.join(self.temp_dir, "papers")
        paper_dir = os.path.join(papers_base, paper_id)
        os.makedirs(paper_dir, exist_ok=True)
        pdf_path = os.path.join(paper_dir, "original.pdf")
        with open(pdf_path, "wb") as f:
            f.write(b"%PDF-1.4 fake")

        mock_download.return_value = pdf_path

        def fake_parse(p, o):
            os.makedirs(os.path.dirname(o), exist_ok=True)
            with open(o, "w") as f:
                f.write("# Test\n\nContent.\n")
        mock_parse.side_effect = fake_parse

        queue_path = os.path.join(self.temp_dir, "download_queue.json")
        with open(queue_path, "w") as f:
            json.dump({"queue": [{"paper_id": paper_id, "url": "http://x", "source_db": "arxiv"}]}, f)

        input_data = SourceAcquisitionInput(
            task_id="test-wm-02",
            config={},
            input_files={"download_queue.json": queue_path},
            context={},
            upstream_module_01={},
        )
        output = self.impl.execute(input_data)
        manifest = self.impl.write_manifest(output)

        self.assertEqual(manifest["module_id"], "02")
        self.assertEqual(manifest["module_name"], "Source Acquisition & Parsing")

    @patch.object(_mod02_impl.PaperDownloader, "download")
    @patch.object(_mod02_impl.PDFParser, "parse")
    def test_write_report(self, mock_parse, mock_download):
        """write_report returns a non-empty Markdown string."""
        paper_id = "test_paper_005"
        papers_base = os.path.join(self.temp_dir, "papers")
        paper_dir = os.path.join(papers_base, paper_id)
        os.makedirs(paper_dir, exist_ok=True)
        pdf_path = os.path.join(paper_dir, "original.pdf")
        with open(pdf_path, "wb") as f:
            f.write(b"%PDF-1.4 fake")

        mock_download.return_value = pdf_path

        def fake_parse(p, o):
            os.makedirs(os.path.dirname(o), exist_ok=True)
            with open(o, "w") as f:
                f.write("# Test\n\nContent.\n")
        mock_parse.side_effect = fake_parse

        queue_path = os.path.join(self.temp_dir, "download_queue.json")
        with open(queue_path, "w") as f:
            json.dump({"queue": [{"paper_id": paper_id, "url": "http://x", "source_db": "arxiv"}]}, f)

        input_data = SourceAcquisitionInput(
            task_id="test-wr-02",
            config={},
            input_files={"download_queue.json": queue_path},
            context={},
            upstream_module_01={},
        )
        output = self.impl.execute(input_data)
        report = self.impl.write_report(output)

        self.assertIsInstance(report, str)
        self.assertIn("Module 02", report)
        self.assertIn("Source Acquisition", report)

    def test_extract_elements(self):
        """_extract_elements correctly extracts equations, figures, tables, citations."""
        text = (
            "# Test Paper\n\n"
            "## Abstract\n\nSome abstract text.\n\n"
            "## Introduction\n\n"
            "We use the equation $$E = mc^2$$ inline.\n\n"
            "See Figure 1 for details.\n\n"
            "As shown in Table 1, results are good.\n\n"
            "This was proposed by Smith et al. [1] and refined in [2, 3].\n\n"
            "| Col1 | Col2 |\n|------|------|\n| a    | b    |\n"
        )
        result = self.impl._extract_elements(text, "test_paper")

        self.assertIn("equations", result)
        self.assertIn("figures", result)
        self.assertIn("tables", result)
        self.assertIn("citations", result)
        self.assertTrue(len(result["equations"]["items"]) > 0)
        self.assertTrue(len(result["figures"]["items"]) > 0)
        self.assertTrue(len(result["tables"]["items"]) > 0)
        self.assertTrue(len(result["citations"]["items"]) > 0)


# ================================================================== #
# Module 03 — Literature Intelligence
# ================================================================== #
class TestModule03LiteratureIntelligence(unittest.TestCase):
    """Tests for the v3 Module 03 implementation."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="v3_mod03_")
        self.impl = LiteratureIntelligenceImplementation()
        self.impl.load_config({
            "output_dir": self.temp_dir,
        })

    def test_instantiation(self):
        """Module 03 implementation can be instantiated."""
        impl = LiteratureIntelligenceImplementation()
        self.assertEqual(impl.MODULE_ID, "03")
        self.assertEqual(impl.MODULE_NAME, "Literature Intelligence")

    def test_load_config(self):
        """load_config sets internal config and initialises components."""
        self.assertIsNotNone(self.impl._extractor)
        self.assertIsNotNone(self.impl._quality_checker)
        self.assertIsNotNone(self.impl._db)

    def test_validate_input_with_md_files(self):
        """validate_input returns True when paper.md is present in upstream."""
        paper_id = "test_paper_010"
        md_path = os.path.join(self.temp_dir, "paper.md")
        with open(md_path, "w") as f:
            f.write("# Test\n\nContent.\n")

        input_data = LiteratureIntelligenceInput(
            task_id="test-03",
            config={},
            input_files={f"papers/{paper_id}/normalized/paper.md": md_path},
            context={},
            upstream_module_02={
                "output_files": {
                    f"papers/{paper_id}/normalized/paper.md": md_path,
                }
            },
        )
        self.assertTrue(self.impl.validate_input(input_data))

    def test_validate_input_without_md_files(self):
        """validate_input returns False when no paper.md is present."""
        input_data = LiteratureIntelligenceInput(
            task_id="test-03",
            config={},
            input_files={},
            context={},
            upstream_module_02={},
        )
        self.assertFalse(self.impl.validate_input(input_data))

    def test_execute_produces_outputs(self):
        """execute produces paper_analysis.json, .md, and index.jsonl."""
        paper_id = "test_paper_020"
        papers_base = os.path.join(self.temp_dir, "papers")
        paper_dir = os.path.join(papers_base, paper_id)
        normalized_dir = os.path.join(paper_dir, "normalized")
        os.makedirs(normalized_dir, exist_ok=True)

        md_path = os.path.join(normalized_dir, "paper.md")
        with open(md_path, "w") as f:
            f.write(
                "# Attention Is All You Need\n\n"
                "## Abstract\n\n"
                "We propose a new architecture called Transformer.\n\n"
                "## Introduction\n\n"
                "We introduce the Transformer, a new architecture based solely on attention.\n\n"
                "## Method\n\n"
                "The core of our model is the scaled dot-product attention.\n"
                "$$\\text{Attention}(Q,K,V) = \\text{softmax}(\\frac{QK^T}{\\sqrt{d_k}})V$$\n\n"
                "## Experiments\n\n"
                "We evaluate on WMT 2014 and achieve BLEU score of 28.4.\n"
                "We compare with RNN and CNN baselines.\n\n"
                "## Conclusion\n\n"
                "We presented the Transformer architecture.\n"
            )

        meta_path = os.path.join(paper_dir, "metadata.json")
        with open(meta_path, "w") as f:
            json.dump({
                "paper_id": paper_id,
                "title": "Attention Is All You Need",
                "authors": ["Vaswani et al."],
                "year": 2017,
                "venue": "NeurIPS",
            }, f)

        input_data = LiteratureIntelligenceInput(
            task_id="test-exec-03",
            config={},
            input_files={},
            context={},
            upstream_module_02={
                "output_files": {
                    f"papers/{paper_id}/normalized/paper.md": md_path,
                    f"papers/{paper_id}/metadata.json": meta_path,
                }
            },
        )
        output = self.impl.execute(input_data)

        self.assertIsInstance(output, LiteratureIntelligenceOutput)
        self.assertIn("paper_analysis.json", output.output_files)
        self.assertIn("paper_analysis.md", output.output_files)
        self.assertIn("literature_analysis_index.jsonl", output.output_files)
        self.assertIn("Module03_Validation_Report.md", output.output_files)
        self.assertEqual(output.manifest["total_papers_analyzed"], 1)

    def test_validate_output(self):
        """validate_output returns True after successful execute."""
        paper_id = "test_paper_021"
        papers_base = os.path.join(self.temp_dir, "papers")
        paper_dir = os.path.join(papers_base, paper_id)
        normalized_dir = os.path.join(paper_dir, "normalized")
        os.makedirs(normalized_dir, exist_ok=True)

        md_path = os.path.join(normalized_dir, "paper.md")
        with open(md_path, "w") as f:
            f.write("# Test Paper\n\n## Abstract\n\nTest abstract.\n\n## Method\n\nTest method.\n")

        input_data = LiteratureIntelligenceInput(
            task_id="test-vo-03",
            config={},
            input_files={},
            context={},
            upstream_module_02={
                "output_files": {
                    f"papers/{paper_id}/normalized/paper.md": md_path,
                }
            },
        )
        output = self.impl.execute(input_data)
        self.assertTrue(self.impl.validate_output(output))

    def test_quality_assessment(self):
        """quality_assessment returns metrics with hard and soft thresholds."""
        paper_id = "test_paper_022"
        papers_base = os.path.join(self.temp_dir, "papers")
        paper_dir = os.path.join(papers_base, paper_id)
        normalized_dir = os.path.join(paper_dir, "normalized")
        os.makedirs(normalized_dir, exist_ok=True)

        md_path = os.path.join(normalized_dir, "paper.md")
        with open(md_path, "w") as f:
            f.write(
                "# Test Paper\n\n## Abstract\n\nAbstract text.\n\n"
                "## Method\n\nMethod content.\n\n"
                "## Experiments\n\nResults.\n\n"
            )

        input_data = LiteratureIntelligenceInput(
            task_id="test-qa-03",
            config={},
            input_files={},
            context={},
            upstream_module_02={
                "output_files": {
                    f"papers/{paper_id}/normalized/paper.md": md_path,
                }
            },
        )
        output = self.impl.execute(input_data)
        qa = self.impl.quality_assessment(output)

        self.assertIn("overall_pass", qa)
        self.assertIn("hard_requirements", qa)
        self.assertIn("soft_thresholds", qa)
        self.assertIn("total_analyzed", qa)

    def test_write_manifest(self):
        """write_manifest returns a dict with module metadata."""
        paper_id = "test_paper_023"
        papers_base = os.path.join(self.temp_dir, "papers")
        paper_dir = os.path.join(papers_base, paper_id)
        normalized_dir = os.path.join(paper_dir, "normalized")
        os.makedirs(normalized_dir, exist_ok=True)

        md_path = os.path.join(normalized_dir, "paper.md")
        with open(md_path, "w") as f:
            f.write("# Test\n\n## Method\n\nContent.\n")

        input_data = LiteratureIntelligenceInput(
            task_id="test-wm-03",
            config={},
            input_files={},
            context={},
            upstream_module_02={
                "output_files": {
                    f"papers/{paper_id}/normalized/paper.md": md_path,
                }
            },
        )
        output = self.impl.execute(input_data)
        manifest = self.impl.write_manifest(output)

        self.assertEqual(manifest["module_id"], "03")
        self.assertEqual(manifest["module_name"], "Literature Intelligence")

    def test_write_report(self):
        """write_report returns a non-empty Markdown string."""
        paper_id = "test_paper_024"
        papers_base = os.path.join(self.temp_dir, "papers")
        paper_dir = os.path.join(papers_base, paper_id)
        normalized_dir = os.path.join(paper_dir, "normalized")
        os.makedirs(normalized_dir, exist_ok=True)

        md_path = os.path.join(normalized_dir, "paper.md")
        with open(md_path, "w") as f:
            f.write("# Test\n\n## Method\n\nContent.\n")

        input_data = LiteratureIntelligenceInput(
            task_id="test-wr-03",
            config={},
            input_files={},
            context={},
            upstream_module_02={
                "output_files": {
                    f"papers/{paper_id}/normalized/paper.md": md_path,
                }
            },
        )
        output = self.impl.execute(input_data)
        report = self.impl.write_report(output)

        self.assertIsInstance(report, str)
        self.assertIn("Module 03", report)
        self.assertIn("Literature Intelligence", report)

    def test_index_jsonl_is_valid(self):
        """literature_analysis_index.jsonl contains valid JSON lines."""
        paper_id = "test_paper_025"
        papers_base = os.path.join(self.temp_dir, "papers")
        paper_dir = os.path.join(papers_base, paper_id)
        normalized_dir = os.path.join(paper_dir, "normalized")
        os.makedirs(normalized_dir, exist_ok=True)

        md_path = os.path.join(normalized_dir, "paper.md")
        with open(md_path, "w") as f:
            f.write("# Test\n\n## Abstract\n\nContent.\n\n## Method\n\nMethod.\n")

        input_data = LiteratureIntelligenceInput(
            task_id="test-idx-03",
            config={},
            input_files={},
            context={},
            upstream_module_02={
                "output_files": {
                    f"papers/{paper_id}/normalized/paper.md": md_path,
                }
            },
        )
        output = self.impl.execute(input_data)
        index_path = output.output_files["literature_analysis_index.jsonl"]

        with open(index_path, "r") as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    self.assertIn("paper_id", entry)
                    self.assertIn("title", entry)


# ================================================================== #
# Integration: Module 01 -> 02 -> 03 chain (mocked)
# ================================================================== #
class TestV3ModuleChain(unittest.TestCase):
    """Integration test for the v3 module chain (mocked)."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="v3_chain_")

    @patch.object(_mod01_impl.PaperDownloader, "search_arxiv")
    @patch.object(_mod01_impl.PaperDownloader, "search_semantic_scholar")
    def test_module01_to_02_handoff(self, mock_ss, mock_arxiv):
        """Module 01 output can be consumed by Module 02 input."""
        # --- Module 01 ---
        mod01 = LiteratureRetrievalImplementation()
        mod01.load_config({
            "output_dir": os.path.join(self.temp_dir, "mod01"),
            "max_papers": 3,
            "databases": ["arxiv", "semantic_scholar"],
        })

        mock_arxiv.return_value = [
            {"paper_id": "chain_001", "title": "Chain Paper",
             "authors": ["Author"], "year": 2024, "venue": "arXiv",
             "pdf_url": "http://example.com/chain.pdf"},
        ]
        mock_ss.return_value = []

        rt_path = os.path.join(self.temp_dir, "research_task.yaml")
        with open(rt_path, "w") as f:
            f.write("research_question: chain test\nkeywords:\n  - chain\n")

        input_01 = LiteratureRetrievalInput(
            task_id="chain-test",
            config={},
            input_files={"research_task.yaml": rt_path},
            context={},
        )
        output_01 = mod01.execute(input_01)

        # Verify Module 01 produced a download_queue.json
        queue_path = output_01.output_files["download_queue.json"]
        self.assertTrue(os.path.exists(queue_path))

        # --- Module 02 ---
        mod02 = SourceAcquisitionImplementation()
        mod02.load_config({
            "output_dir": os.path.join(self.temp_dir, "mod02"),
        })

        # Module 02 can use Module 01's output as input
        input_02 = SourceAcquisitionInput(
            task_id="chain-test",
            config={},
            input_files={"download_queue.json": queue_path},
            context={},
            upstream_module_01={
                "output_files": output_01.output_files,
                "manifest": output_01.manifest,
            },
        )
        self.assertTrue(mod02.validate_input(input_02))


if __name__ == "__main__":
    unittest.main()

"""
v3 Reasoning Module Tests

Verifies that the v3 facade/adapter implementations:
1. Can be imported and instantiated.
2. Implement the v3 module interfaces correctly.
3. Produce the required output files.
4. The LLM provider adapter bridges v3 providers to existing reasoning code.
5. The v3 LLM provider is compatible with the existing reasoning modules.

These tests do NOT modify any existing code in ``reasoning/`` or
``tests/test_llm_reasoning.py``.  They only exercise the new v3 files.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
import unittest
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------

_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

_V3_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _V3_ROOT not in sys.path:
    sys.path.insert(0, _V3_ROOT)


# ---------------------------------------------------------------------------
# Import helpers -- module directories start with digits so we must use
# importlib rather than ``from ... import ...`` syntax.
# ---------------------------------------------------------------------------

def _import_v3_module(dotted_name: str):
    """Import a v3 module by its dotted name (e.g. ``Research_Agent_v3.modules.04_research_landscape.implementation``)."""
    return importlib.import_module(dotted_name)


# ---------------------------------------------------------------------------
# Test data helpers
# ---------------------------------------------------------------------------

def _make_paper_analysis_json(path: str) -> str:
    """Write a minimal paper_analysis.json and return its path."""
    data = [
        {
            "paper_id": "paper_001",
            "title": "Safety Alignment for Vision-Language Models via RLHF",
            "main_contribution": "Proposes RLHF-based safety alignment for VLMs",
            "methodology": "reinforcement learning from human feedback for safety",
            "abstract": "We study safety alignment in vision-language models using RLHF.",
            "key_findings": ["RLHF improves safety", "Output-space alignment is limited"],
            "limitations": ["output-space only", "inference latency"],
            "year": "2024",
            "venue": "NeurIPS",
        },
        {
            "paper_id": "paper_002",
            "title": "Jailbreak Attacks on Multimodal LLMs",
            "main_contribution": "Demonstrates jailbreak vulnerabilities in multimodal models",
            "methodology": "adversarial prompt injection and image perturbation",
            "abstract": "We show that multimodal LLMs are vulnerable to jailbreak attacks.",
            "key_findings": ["VLMs can be jailbroken", "Safety filters are bypassable"],
            "limitations": ["limited attack types", "no defense proposed"],
            "year": "2024",
            "venue": "ICLR",
        },
        {
            "paper_id": "paper_003",
            "title": "Efficient Safety Fine-tuning for Large Language Models",
            "main_contribution": "Efficient safety fine-tuning method",
            "methodology": "parameter-efficient fine-tuning for safety",
            "abstract": "We propose an efficient safety fine-tuning approach for LLMs.",
            "key_findings": ["Efficient safety training", "Minimal performance degradation"],
            "limitations": ["text-only", "not tested on VLMs"],
            "year": "2023",
            "venue": "ICML",
        },
    ]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def _make_gap_candidates_json(path: str) -> str:
    """Write a minimal gap_candidates.json."""
    data = {
        "gaps": [
            {
                "description": "Representation-space safety alignment is unexplored",
                "gap_type": "unaddressed",
                "supporting_papers": ["paper_001", "paper_003"],
                "novelty_score": 0.8,
            },
            {
                "description": "No unified defense against cross-modal jailbreak attacks",
                "gap_type": "contradiction",
                "supporting_papers": ["paper_002"],
                "novelty_score": 0.7,
            },
        ]
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def _make_method_spec_json(path: str) -> str:
    """Write a minimal method_spec.json."""
    data = {
        "method_name": "RepSafe",
        "description": "Representation-space safety alignment via projection",
        "components": [
            {"name": "safety_encoder", "type": "encoder", "params": {"dim": 768}},
            {"name": "projection_matrix", "type": "layer", "params": {"rank": 64}},
        ],
        "input_schema": {"type": "multimodal", "fields": ["text", "image"]},
        "output_schema": {"type": "safety_score", "fields": ["score"]},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def _make_research_direction_md(path: str) -> str:
    """Write a minimal final_research_direction.md."""
    content = (
        "# Final Research Direction\n\n"
        "## Selected Direction\n\n"
        "**Representation-space safety alignment for VLMs**\n\n"
        "## Justification\n\n"
        "Current safety methods operate in output space, leaving "
        "representation-level vulnerabilities unaddressed.\n\n"
        "## Novelty Argument\n\n"
        "No existing work explores representation-space safety projection.\n\n"
        "## Feasibility Assessment\n\n"
        "The method can be implemented as a lightweight projection layer.\n\n"
        "## Expected Contribution\n\n"
        "Improved defense against jailbreak attacks with minimal overhead.\n"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


# ---------------------------------------------------------------------------
# LLM provider adapter tests
# ---------------------------------------------------------------------------

class TestLLMProviderAdapter(unittest.TestCase):
    """Verify the adapter bridges v3 providers to existing reasoning code."""

    def test_adapter_generate_with_context(self) -> None:
        """Adapter forwards context as kwarg."""
        mod = _import_v3_module(
            "Research_Agent_v3.modules.04_research_landscape.implementation"
        )
        LLMProviderAdapter = mod.LLMProviderAdapter

        class StubProvider:
            def __init__(self) -> None:
                self.calls: List[Dict[str, Any]] = []

            def generate(self, prompt: str, **kwargs: Any) -> str:
                self.calls.append({"prompt": prompt, **kwargs})
                return "stub response"

            def is_available(self) -> bool:
                return True

        stub = StubProvider()
        adapter = LLMProviderAdapter(stub)
        result = adapter.generate("test prompt", context="ctx")
        self.assertEqual(result, "stub response")
        self.assertEqual(stub.calls[0]["prompt"], "test prompt")
        self.assertEqual(stub.calls[0]["context"], "ctx")

    def test_adapter_generate_without_context(self) -> None:
        """Adapter works when existing code calls generate(prompt) only."""
        mod = _import_v3_module(
            "Research_Agent_v3.modules.04_research_landscape.implementation"
        )
        LLMProviderAdapter = mod.LLMProviderAdapter

        class StubProvider:
            def generate(self, prompt: str, **kwargs: Any) -> str:
                return f"processed:{prompt}"

            def is_available(self) -> bool:
                return True

        adapter = LLMProviderAdapter(StubProvider())
        result = adapter.generate("hello")
        self.assertEqual(result, "processed:hello")

    def test_adapter_is_available(self) -> None:
        mod = _import_v3_module(
            "Research_Agent_v3.modules.04_research_landscape.implementation"
        )
        LLMProviderAdapter = mod.LLMProviderAdapter

        class Available:
            def is_available(self) -> bool:
                return True

            def generate(self, prompt: str, **kw: Any) -> str:
                return ""

        class Unavailable:
            def is_available(self) -> bool:
                return False

            def generate(self, prompt: str, **kw: Any) -> str:
                return ""

        self.assertTrue(LLMProviderAdapter(Available()).is_available())
        self.assertFalse(LLMProviderAdapter(Unavailable()).is_available())

    def test_v3_provider_compatible_with_existing_reasoning(self) -> None:
        """The v3 MockProvider is directly usable by existing reasoning code."""
        v3_llm_mod = _import_v3_module(
            "Research_Agent_v3.infrastructure.llm.llm_provider"
        )
        MockProvider = v3_llm_mod.MockProvider

        from reasoning.gap_analyzer.gap_analyzer import GapAnalyzer

        v3_mock = MockProvider()
        analyzer = GapAnalyzer(llm_provider=v3_mock)
        self.assertIsNotNone(analyzer.llm_provider)
        result = analyzer.llm_provider.generate("gap analysis prompt")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)


# ---------------------------------------------------------------------------
# Module 04 tests
# ---------------------------------------------------------------------------

class TestModule04Implementation(unittest.TestCase):
    """Test Module 04 -- Research Landscape."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp(prefix="v3_mod04_")
        self.paper_analysis_path = _make_paper_analysis_json(
            os.path.join(self.tmpdir, "paper_analysis.json")
        )
        self.output_dir = os.path.join(self.tmpdir, "output")

        mod = _import_v3_module(
            "Research_Agent_v3.modules.04_research_landscape.implementation"
        )
        self.ResearchLandscapeModule = mod.ResearchLandscapeModule

        iface = _import_v3_module(
            "Research_Agent_v3.modules.04_research_landscape.interface"
        )
        self.ResearchLandscapeInput = iface.ResearchLandscapeInput
        self.Module04Interface = iface.Module04Interface

    def test_import_and_instantiate(self) -> None:
        module = self.ResearchLandscapeModule()
        self.assertIsNotNone(module)
        self.assertEqual(module.MODULE_ID, "04")

    def test_implements_interface(self) -> None:
        self.assertTrue(issubclass(self.ResearchLandscapeModule, self.Module04Interface))

    def test_execute_produces_all_outputs(self) -> None:
        module = self.ResearchLandscapeModule()
        module.load_config({"output_dir": self.output_dir})

        input_data = self.ResearchLandscapeInput(
            task_id="test_04",
            config={},
            input_files={"paper_analysis.json": self.paper_analysis_path},
            context={},
            upstream_module_03={},
        )
        output = module.execute(input_data)

        required = [
            "research_landscape.md",
            "taxonomy.json",
            "trend_analysis.json",
            "contradiction_map.json",
            "gap_candidates.json",
        ]
        for name in required:
            self.assertIn(name, output.output_files, f"Missing output: {name}")
            path = output.output_files[name]
            self.assertTrue(os.path.exists(path), f"File not found: {path}")

    def test_taxonomy_has_categories(self) -> None:
        module = self.ResearchLandscapeModule()
        module.load_config({"output_dir": self.output_dir})

        input_data = self.ResearchLandscapeInput(
            task_id="test_04_tax",
            config={},
            input_files={"paper_analysis.json": self.paper_analysis_path},
            context={},
            upstream_module_03={},
        )
        output = module.execute(input_data)

        taxonomy_path = output.output_files["taxonomy.json"]
        with open(taxonomy_path, "r", encoding="utf-8") as f:
            taxonomy = json.load(f)
        self.assertIn("categories", taxonomy)
        self.assertGreaterEqual(len(taxonomy["categories"]), 1)

    def test_gap_candidates_has_gaps(self) -> None:
        module = self.ResearchLandscapeModule()
        module.load_config({"output_dir": self.output_dir})

        input_data = self.ResearchLandscapeInput(
            task_id="test_04_gap",
            config={},
            input_files={"paper_analysis.json": self.paper_analysis_path},
            context={},
            upstream_module_03={},
        )
        output = module.execute(input_data)

        gap_path = output.output_files["gap_candidates.json"]
        with open(gap_path, "r", encoding="utf-8") as f:
            gaps = json.load(f)
        self.assertIn("gaps", gaps)
        self.assertGreaterEqual(len(gaps["gaps"]), 1)

    def test_quality_assessment(self) -> None:
        module = self.ResearchLandscapeModule()
        module.load_config({"output_dir": self.output_dir})

        input_data = self.ResearchLandscapeInput(
            task_id="test_04_qa",
            config={},
            input_files={"paper_analysis.json": self.paper_analysis_path},
            context={},
            upstream_module_03={},
        )
        output = module.execute(input_data)
        qa = module.quality_assessment(output)
        self.assertIn("passed", qa)
        self.assertIn("details", qa)

    def test_write_report(self) -> None:
        module = self.ResearchLandscapeModule()
        module.load_config({"output_dir": self.output_dir})

        input_data = self.ResearchLandscapeInput(
            task_id="test_04_report",
            config={},
            input_files={"paper_analysis.json": self.paper_analysis_path},
            context={},
            upstream_module_03={},
        )
        output = module.execute(input_data)
        report = module.write_report(output)
        self.assertIsInstance(report, str)
        self.assertIn("Module 04", report)


# ---------------------------------------------------------------------------
# Module 05 tests
# ---------------------------------------------------------------------------

class TestModule05Implementation(unittest.TestCase):
    """Test Module 05 -- Innovation Reasoning."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp(prefix="v3_mod05_")
        self.paper_analysis_path = _make_paper_analysis_json(
            os.path.join(self.tmpdir, "paper_analysis.json")
        )
        self.gap_candidates_path = _make_gap_candidates_json(
            os.path.join(self.tmpdir, "gap_candidates.json")
        )
        self.output_dir = os.path.join(self.tmpdir, "output")

        mod = _import_v3_module(
            "Research_Agent_v3.modules.05_innovation_reasoning.implementation"
        )
        self.InnovationReasoningModule = mod.InnovationReasoningModule

        iface = _import_v3_module(
            "Research_Agent_v3.modules.05_innovation_reasoning.interface"
        )
        self.InnovationReasoningInput = iface.InnovationReasoningInput
        self.Module05Interface = iface.Module05Interface

    def test_import_and_instantiate(self) -> None:
        module = self.InnovationReasoningModule()
        self.assertIsNotNone(module)
        self.assertEqual(module.MODULE_ID, "05")

    def test_implements_interface(self) -> None:
        self.assertTrue(issubclass(self.InnovationReasoningModule, self.Module05Interface))

    def test_execute_produces_all_outputs(self) -> None:
        module = self.InnovationReasoningModule()
        module.load_config({"output_dir": self.output_dir})

        input_data = self.InnovationReasoningInput(
            task_id="test_05",
            config={},
            input_files={
                "paper_analysis.json": self.paper_analysis_path,
                "gap_candidates.json": self.gap_candidates_path,
            },
            context={},
            upstream_module_03={},
            upstream_module_04={},
        )
        output = module.execute(input_data)

        required = [
            "innovation_candidates.json",
            "novelty_analysis.md",
            "final_research_direction.md",
        ]
        for name in required:
            self.assertIn(name, output.output_files, f"Missing output: {name}")
            path = output.output_files[name]
            self.assertTrue(os.path.exists(path), f"File not found: {path}")

    def test_innovation_candidates_have_required_fields(self) -> None:
        module = self.InnovationReasoningModule()
        module.load_config({"output_dir": self.output_dir, "num_innovations": 2})

        input_data = self.InnovationReasoningInput(
            task_id="test_05_fields",
            config={},
            input_files={
                "paper_analysis.json": self.paper_analysis_path,
                "gap_candidates.json": self.gap_candidates_path,
            },
            context={},
            upstream_module_03={},
            upstream_module_04={},
        )
        output = module.execute(input_data)

        candidates_path = output.output_files["innovation_candidates.json"]
        with open(candidates_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("candidates", data)
        self.assertGreaterEqual(len(data["candidates"]), 1)
        cand = data["candidates"][0]
        for field in ["title", "description", "novelty_score",
                       "feasibility_score", "impact_score", "source_gap"]:
            self.assertIn(field, cand, f"Missing field in candidate: {field}")


# ---------------------------------------------------------------------------
# Module 06 tests
# ---------------------------------------------------------------------------

class TestModule06Implementation(unittest.TestCase):
    """Test Module 06 -- Theory & Method."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp(prefix="v3_mod06_")
        self.direction_path = _make_research_direction_md(
            os.path.join(self.tmpdir, "final_research_direction.md")
        )
        self.output_dir = os.path.join(self.tmpdir, "output")

        mod = _import_v3_module(
            "Research_Agent_v3.modules.06_theory_method.implementation"
        )
        self.TheoryMethodModule = mod.TheoryMethodModule

        iface = _import_v3_module(
            "Research_Agent_v3.modules.06_theory_method.interface"
        )
        self.TheoryMethodInput = iface.TheoryMethodInput
        self.Module06Interface = iface.Module06Interface

    def test_import_and_instantiate(self) -> None:
        module = self.TheoryMethodModule()
        self.assertIsNotNone(module)
        self.assertEqual(module.MODULE_ID, "06")

    def test_implements_interface(self) -> None:
        self.assertTrue(issubclass(self.TheoryMethodModule, self.Module06Interface))

    def test_execute_produces_all_outputs(self) -> None:
        module = self.TheoryMethodModule()
        module.load_config({"output_dir": self.output_dir})

        input_data = self.TheoryMethodInput(
            task_id="test_06",
            config={},
            input_files={"final_research_direction.md": self.direction_path},
            context={},
            upstream_module_05={},
        )
        output = module.execute(input_data)

        required = [
            "method_spec.json",
            "theory_framework.md",
            "method_design.md",
            "mathematical_formulation.md",
            "algorithm_design.md",
        ]
        for name in required:
            self.assertIn(name, output.output_files, f"Missing output: {name}")
            path = output.output_files[name]
            self.assertTrue(os.path.exists(path), f"File not found: {path}")

    def test_method_spec_has_required_fields(self) -> None:
        module = self.TheoryMethodModule()
        module.load_config({"output_dir": self.output_dir})

        input_data = self.TheoryMethodInput(
            task_id="test_06_spec",
            config={},
            input_files={"final_research_direction.md": self.direction_path},
            context={},
            upstream_module_05={},
        )
        output = module.execute(input_data)

        spec_path = output.output_files["method_spec.json"]
        with open(spec_path, "r", encoding="utf-8") as f:
            spec = json.load(f)
        for field in ["method_name", "description", "components",
                       "input_schema", "output_schema"]:
            self.assertIn(field, spec, f"Missing field in method_spec: {field}")


# ---------------------------------------------------------------------------
# Module 07 tests
# ---------------------------------------------------------------------------

class TestModule07Implementation(unittest.TestCase):
    """Test Module 07 -- Experiment Planning."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp(prefix="v3_mod07_")
        self.method_spec_path = _make_method_spec_json(
            os.path.join(self.tmpdir, "method_spec.json")
        )
        self.output_dir = os.path.join(self.tmpdir, "output")

        mod = _import_v3_module(
            "Research_Agent_v3.modules.07_experiment_planning.implementation"
        )
        self.ExperimentPlanningModule = mod.ExperimentPlanningModule

        iface = _import_v3_module(
            "Research_Agent_v3.modules.07_experiment_planning.interface"
        )
        self.ExperimentPlanningInput = iface.ExperimentPlanningInput
        self.Module07Interface = iface.Module07Interface

    def test_import_and_instantiate(self) -> None:
        module = self.ExperimentPlanningModule()
        self.assertIsNotNone(module)
        self.assertEqual(module.MODULE_ID, "07")

    def test_implements_interface(self) -> None:
        self.assertTrue(issubclass(self.ExperimentPlanningModule, self.Module07Interface))

    def test_execute_produces_all_outputs(self) -> None:
        module = self.ExperimentPlanningModule()
        module.load_config({"output_dir": self.output_dir})

        input_data = self.ExperimentPlanningInput(
            task_id="test_07",
            config={},
            input_files={"method_spec.json": self.method_spec_path},
            context={},
            upstream_module_06={},
        )
        output = module.execute(input_data)

        required = [
            "experiment_plan.md",
            "experiment_matrix.yaml",
            "claim_evidence_plan.json",
            "paper_figure_plan.yaml",
        ]
        for name in required:
            self.assertIn(name, output.output_files, f"Missing output: {name}")
            path = output.output_files[name]
            self.assertTrue(os.path.exists(path), f"File not found: {path}")

    def test_experiment_matrix_has_experiments(self) -> None:
        module = self.ExperimentPlanningModule()
        module.load_config({"output_dir": self.output_dir})

        input_data = self.ExperimentPlanningInput(
            task_id="test_07_matrix",
            config={},
            input_files={"method_spec.json": self.method_spec_path},
            context={},
            upstream_module_06={},
        )
        output = module.execute(input_data)

        matrix_path = output.output_files["experiment_matrix.yaml"]
        self.assertTrue(os.path.getsize(matrix_path) > 0)
        with open(matrix_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("experiments:", content)

    def test_claim_evidence_plan_has_claims(self) -> None:
        module = self.ExperimentPlanningModule()
        module.load_config({"output_dir": self.output_dir})

        input_data = self.ExperimentPlanningInput(
            task_id="test_07_claims",
            config={},
            input_files={"method_spec.json": self.method_spec_path},
            context={},
            upstream_module_06={},
        )
        output = module.execute(input_data)

        claim_path = output.output_files["claim_evidence_plan.json"]
        with open(claim_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("claims", data)
        self.assertGreaterEqual(len(data["claims"]), 1)


# ---------------------------------------------------------------------------
# V3 LLM provider compatibility test
# ---------------------------------------------------------------------------

class TestV3LLMProviderCompatibility(unittest.TestCase):
    """Verify the v3 LLM provider is compatible with existing reasoning code."""

    def test_v3_mock_provider_works_with_gap_analyzer(self) -> None:
        v3_llm_mod = _import_v3_module(
            "Research_Agent_v3.infrastructure.llm.llm_provider"
        )
        MockProvider = v3_llm_mod.MockProvider

        from reasoning.gap_analyzer.gap_analyzer import GapAnalyzer

        provider = MockProvider()
        analyzer = GapAnalyzer(llm_provider=provider)
        self.assertIsNotNone(analyzer.llm_provider)
        result = provider.generate("analyze research gap")
        self.assertIsInstance(result, str)

    def test_v3_mock_provider_works_with_scientific_reasoner(self) -> None:
        v3_llm_mod = _import_v3_module(
            "Research_Agent_v3.infrastructure.llm.llm_provider"
        )
        MockProvider = v3_llm_mod.MockProvider

        from reasoning.scientific_reasoner import (
            InnovationGenerator,
            ContradictionDetector,
            CausalAnalyzer,
            TheoryBuilder,
            NoveltyChecker,
        )

        provider = MockProvider()

        gen = InnovationGenerator(llm_provider=provider, llm_enabled=True)
        self.assertTrue(gen.llm_enabled)

        det = ContradictionDetector(llm_provider=provider, llm_enabled=True)
        self.assertTrue(det.llm_enabled)

        ca = CausalAnalyzer(llm_provider=provider, llm_enabled=True)
        self.assertTrue(ca.llm_enabled)

        tb = TheoryBuilder(llm_provider=provider, llm_enabled=True)
        self.assertTrue(tb.llm_enabled)

        nc = NoveltyChecker(llm_provider=provider, llm_enabled=True)
        self.assertTrue(nc.llm_enabled)

    def test_v3_provider_factory_creates_mock(self) -> None:
        v3_llm_mod = _import_v3_module(
            "Research_Agent_v3.infrastructure.llm.llm_provider"
        )
        LLMProviderFactory = v3_llm_mod.LLMProviderFactory
        MockProvider = v3_llm_mod.MockProvider

        provider = LLMProviderFactory.create_provider({"type": "mock"})
        self.assertIsInstance(provider, MockProvider)
        self.assertTrue(provider.is_available())

    def test_v3_provider_has_required_methods(self) -> None:
        v3_llm_mod = _import_v3_module(
            "Research_Agent_v3.infrastructure.llm.llm_provider"
        )
        MockProvider = v3_llm_mod.MockProvider

        provider = MockProvider()
        self.assertTrue(hasattr(provider, "generate"))
        self.assertTrue(callable(provider.generate))
        self.assertTrue(hasattr(provider, "is_available"))
        self.assertTrue(callable(provider.is_available))
        self.assertTrue(hasattr(provider, "get_name"))
        self.assertTrue(callable(provider.get_name))

    def test_v3_provider_generate_accepts_prompt_only(self) -> None:
        v3_llm_mod = _import_v3_module(
            "Research_Agent_v3.infrastructure.llm.llm_provider"
        )
        MockProvider = v3_llm_mod.MockProvider

        provider = MockProvider()
        result = provider.generate("innovation generation prompt")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)


# ---------------------------------------------------------------------------
# Full pipeline integration test
# ---------------------------------------------------------------------------

class TestV3PipelineIntegration(unittest.TestCase):
    """End-to-end test of modules 04 -> 05 -> 06 -> 07."""

    def test_full_pipeline(self) -> None:
        mod04_impl = _import_v3_module(
            "Research_Agent_v3.modules.04_research_landscape.implementation"
        )
        mod05_impl = _import_v3_module(
            "Research_Agent_v3.modules.05_innovation_reasoning.implementation"
        )
        mod06_impl = _import_v3_module(
            "Research_Agent_v3.modules.06_theory_method.implementation"
        )
        mod07_impl = _import_v3_module(
            "Research_Agent_v3.modules.07_experiment_planning.implementation"
        )
        mod04_iface = _import_v3_module(
            "Research_Agent_v3.modules.04_research_landscape.interface"
        )
        mod05_iface = _import_v3_module(
            "Research_Agent_v3.modules.05_innovation_reasoning.interface"
        )
        mod06_iface = _import_v3_module(
            "Research_Agent_v3.modules.06_theory_method.interface"
        )
        mod07_iface = _import_v3_module(
            "Research_Agent_v3.modules.07_experiment_planning.interface"
        )

        tmpdir = tempfile.mkdtemp(prefix="v3_pipeline_")

        # Module 04
        paper_path = _make_paper_analysis_json(
            os.path.join(tmpdir, "paper_analysis.json")
        )
        mod04_dir = os.path.join(tmpdir, "mod04")
        mod04 = mod04_impl.ResearchLandscapeModule()
        mod04.load_config({"output_dir": mod04_dir})
        out04 = mod04.execute(mod04_iface.ResearchLandscapeInput(
            task_id="pipeline",
            config={},
            input_files={"paper_analysis.json": paper_path},
            context={},
            upstream_module_03={},
        ))
        self.assertGreater(len(out04.output_files), 0)

        # Module 05
        mod05_dir = os.path.join(tmpdir, "mod05")
        mod05 = mod05_impl.InnovationReasoningModule()
        mod05.load_config({"output_dir": mod05_dir, "num_innovations": 1})
        out05 = mod05.execute(mod05_iface.InnovationReasoningInput(
            task_id="pipeline",
            config={},
            input_files={
                "paper_analysis.json": paper_path,
                "gap_candidates.json": out04.output_files.get("gap_candidates.json", ""),
            },
            context={},
            upstream_module_03={},
            upstream_module_04={},
        ))
        self.assertIn("final_research_direction.md", out05.output_files)

        # Module 06
        mod06_dir = os.path.join(tmpdir, "mod06")
        mod06 = mod06_impl.TheoryMethodModule()
        mod06.load_config({"output_dir": mod06_dir})
        out06 = mod06.execute(mod06_iface.TheoryMethodInput(
            task_id="pipeline",
            config={},
            input_files={
                "final_research_direction.md": out05.output_files["final_research_direction.md"],
            },
            context={},
            upstream_module_05={},
        ))
        self.assertIn("method_spec.json", out06.output_files)

        # Module 07
        mod07_dir = os.path.join(tmpdir, "mod07")
        mod07 = mod07_impl.ExperimentPlanningModule()
        mod07.load_config({"output_dir": mod07_dir})
        out07 = mod07.execute(mod07_iface.ExperimentPlanningInput(
            task_id="pipeline",
            config={},
            input_files={
                "method_spec.json": out06.output_files["method_spec.json"],
            },
            context={},
            upstream_module_06={},
        ))
        self.assertIn("experiment_plan.md", out07.output_files)


if __name__ == "__main__":
    unittest.main(verbosity=2)

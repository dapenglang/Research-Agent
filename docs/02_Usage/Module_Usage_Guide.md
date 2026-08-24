# Module Usage Guide — Research Agent v3

**Date:** 2026-08-15
**All schemas verified from actual code (`schema.py`, `manifest.yaml`, `interface.py`)**

---

## Pipeline Overview

```
01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 10 → 11 → 12 → 13
                                    ↘ 09 ↗
```

Module 10 (Result Analysis) can route back to: 09 (experiment), 07 (plan), 06 (method), 05 (innovation), or pass forward to 11 (figure/table).

Decision targets from Module 10:
- `PASS_TO_FIGURE_TABLE` → Module 11
- `RETURN_TO_EXPERIMENT` → Module 09
- `RETURN_TO_EXPERIMENT_PLAN` → Module 07
- `RETURN_TO_METHOD` → Module 06
- `RETURN_TO_INNOVATION` → Module 05
- `HUMAN_REVIEW_REQUIRED` → Stops pipeline

---

## Module 01 — Literature Retrieval

**Function:** Retrieves relevant literature from databases based on the research task, producing metadata, a download queue, and a literature manifest.

**Input:** `research_task.yaml` (the pipeline task config)

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `research_question` | str | Yes | — |
| `keywords` | List[str] | Yes | — |
| `domain` | str | Yes | — |
| `max_papers` | int | No | 100 |
| `date_range` | Tuple[str, str] | No | — |
| `databases` | List[str] | No | `['semantic_scholar', 'arxiv', 'pubmed']` |

**Output:**

| File | Key Fields |
|------|------------|
| `literature_manifest.json` | `total_papers`, `search_queries`, `databases_queried`, `retrieval_timestamp` |
| `paper_metadata.jsonl` | `paper_id`, `title`, `authors`, `abstract`, `year`, `doi`, `source_db`, `url`, `citation_count` |
| `download_queue.json` | `queue[].paper_id`, `queue[].url`, `queue[].source_db`, `queue[].priority` |

**Dependencies:** Upstream: none (entry point). Downstream: 02, 03.

**Run via CLI:** `python -m Research_Agent_v3.cli.cli start --task research_task.yaml`

**To run standalone:** Prepare a `research_task.yaml` with the input fields above.

---

## Module 02 — Source Acquisition & Parsing

**Function:** Downloads papers from the queue, parses PDFs into normalized Markdown, and extracts equations, figures, tables, and citations with provenance tracking.

**Input:** `download_queue.json` (from Module 01)

| Field | Type | Required |
|-------|------|----------|
| `queue` | List[Dict] | Yes |
| `queue[].paper_id` | str | Yes |
| `queue[].url` | str | Yes |
| `queue[].source_db` | str | Yes |

**Output (per paper `papers/<paper_id>/`):**

| File | Key Fields |
|------|------------|
| `metadata.json` | `paper_id`, `title`, `authors`, `year`, `doi`, `pages` |
| `normalized/paper.md` | `content`, `sections[].heading`, `sections[].content` |
| `equations.json` | `equations[].latex`, `equations[].label`, `equations[].page` |
| `figures.json` | `figures[].caption`, `figures[].page` |
| `tables.json` | `tables[].caption`, `tables[].rows` |
| `citations.json` | `citations[].raw_text`, `citations[].key` |
| `provenance.json` | `paper_id`, `download_url`, `download_timestamp`, `parser_version`, `source_hash` |

**Dependencies:** Upstream: 01. Downstream: 03.

---

## Module 03 — Literature Intelligence

**Function:** Performs deep analysis of normalized papers to extract contributions, methods, datasets, limitations, and relationships, producing structured per-paper analysis and a cross-paper index.

**Input:** `papers/<paper_id>/normalized/paper.md` (from Module 02)

| Field | Type | Required |
|-------|------|----------|
| `content` | str | Yes |
| `sections` | List[Dict] | Yes |

**Output:**

| File | Key Fields |
|------|------------|
| `paper_analysis.json` | `paper_id`, `main_contribution`, `methodology`, `datasets_used`, `limitations`, `key_findings`, `future_work`, `research_type` |
| `literature_analysis_index.jsonl` | `paper_id`, `title`, `main_contribution`, `methodology`, `year` |

**Dependencies:** Upstream: 02. Downstream: 04, 05.

---

## Module 04 — Research Landscape & Gap Analysis

**Function:** Synthesizes per-paper analyses into a research landscape, building taxonomies, trend analysis, contradiction maps, and identifying gap candidates for innovation.

**Input:** `paper_analysis.json` (from Module 03)

| Field | Type | Required |
|-------|------|----------|
| `paper_id` | str | Yes |
| `main_contribution` | str | Yes |
| `methodology` | str | Yes |
| `key_findings` | List[str] | Yes |
| `limitations` | List[str] | No |

**Output:**

| File | Key Fields |
|------|------------|
| `taxonomy.json` | `categories[].name`, `categories[].papers`, `categories[].subcategories` |
| `trend_analysis.json` | `trends[].topic`, `trends[].trajectory`, `trends[].key_papers` |
| `contradiction_map.json` | `contradictions[].topic`, `contradictions[].paper_a`, `contradictions[].paper_b`, `contradictions[].description` |
| `gap_candidates.json` | `gaps[].description`, `gaps[].gap_type`, `gaps[].supporting_papers`, `gaps[].novelty_score` |

**Dependencies:** Upstream: 03. Downstream: 05.

---

## Module 05 — Innovation & Novelty Reasoning

**Function:** Evaluates gap candidates for novelty and feasibility, generating innovation candidates and selecting a final research direction with justified reasoning.

**Input:**

| File | Key Fields |
|------|------------|
| `gap_candidates.json` (from 04) | `gaps[].description`, `gaps[].gap_type`, `gaps[].supporting_papers` |
| `paper_analysis.json` (from 03) | `paper_id`, `main_contribution`, `methodology` |

**Output:**

| File | Key Fields |
|------|------------|
| `innovation_candidates.json` | `candidates[].title`, `candidates[].description`, `candidates[].novelty_score`, `candidates[].feasibility_score`, `candidates[].impact_score`, `candidates[].source_gap` |
| `final_research_direction.md` | `selected_direction`, `justification`, `novelty_argument`, `feasibility_assessment`, `expected_contribution` |

**Dependencies:** Upstream: 03, 04. Downstream: 06.

---

## Module 06 — Theory & Method Design

**Function:** Designs the theoretical framework, method specification, mathematical formulation, and algorithm design based on the selected research direction.

**Input:** `final_research_direction.md` (from Module 05)

| Field | Type | Required |
|-------|------|----------|
| `selected_direction` | str | Yes |
| `justification` | str | Yes |
| `novelty_argument` | str | Yes |

**Output:**

| File | Key Fields |
|------|------------|
| `method_spec.json` | `method_name`, `description`, `components[].name`, `components[].type`, `components[].params`, `input_schema`, `output_schema`, `hyperparameters`, `dependencies` |
| `theory_framework.md` | `theoretical_basis`, `assumptions`, `propositions` |
| `mathematical_formulation.md` | `notations`, `equations[].latex`, `equations[].description`, `derivations` |
| `algorithm_design.md` | `algorithms[].name`, `algorithms[].pseudocode`, `algorithms[].complexity` |

**Dependencies:** Upstream: 05. Downstream: 07, 08, 09, 11.

---

## Module 07 — Experiment Planning

**Function:** Translates the method specification into a concrete experiment plan with experiment matrix, claim-evidence mapping, and paper figure plan.

**Input:** `method_spec.json` (from Module 06)

| Field | Type | Required |
|-------|------|----------|
| `method_name` | str | Yes |
| `components` | List[Dict] | Yes |
| `input_schema` | Dict | Yes |
| `output_schema` | Dict | Yes |
| `hyperparameters` | Dict[str, Any] | No |

**Output:**

| File | Key Fields |
|------|------------|
| `experiment_matrix.yaml` | `experiments[].id`, `experiments[].name`, `experiments[].type`, `experiments[].data_origin` (allowed: `synthetic`, `real`), `experiments[].parameters`, `experiments[].claims_addressed` |
| `claim_evidence_plan.json` | `claims[].id`, `claims[].statement`, `claims[].evidence_type`, `claims[].experiments`, `claims[].pass_criteria` |
| `paper_figure_plan.yaml` | `figures[].id`, `figures[].title`, `figures[].type`, `figures[].data_source`, `tables[].id`, `tables[].title`, `tables[].data_source` |

**Dependencies:** Upstream: 06. Downstream: 08, 09, 10, 11.

---

## Module 08 — Synthetic Experiment Engine

**Function:** Executes synthetic experiments based on the method specification and experiment matrix. All outputs tagged `data_origin='synthetic'`. Backend adapters (e.g. SAMRA Monte Carlo) are pluggable, NOT built into this module.

**Input:**

| File | Key Fields |
|------|------------|
| `method_spec.json` (from 06) | `method_name`, `components`, `hyperparameters` |
| `experiment_matrix.yaml` (from 07) | `experiments[].id`, `experiments[].data_origin` (**must be `synthetic`**), `experiments[].parameters` |
| `claim_evidence_plan.json` (from 07) | `claims[].id`, `claims[].pass_criteria` |

**Output:**

| File | Key Fields |
|------|------------|
| `synthetic_results/metrics.csv` | `experiment_id`, `metric_name`, `metric_value`, `data_origin` (**must be `synthetic`**) |
| `synthetic_results/statistics.json` | `experiment_id`, `summary_stats`, `confidence_intervals`, `data_origin` (**must be `synthetic`**) |
| `synthetic_results/provenance.json` | `experiments_run`, `execution_timestamp`, `adapter_used`, `adapter_version`, `data_origin`, `environment` |

**Dependencies:** Upstream: 06, 07. Downstream: 10, 11.

---

## Module 09 — Real Experiment Engine

**Function:** Executes real-world experiments based on the method specification and experiment matrix. All outputs tagged `data_origin='real'`. SAMRA is an adapter/plugin, NOT built into this module.

**Input:**

| File | Key Fields |
|------|------------|
| `method_spec.json` (from 06) | `method_name`, `components`, `hyperparameters` |
| `experiment_matrix.yaml` (from 07) | `experiments[].id`, `experiments[].data_origin` (**must be `real`**), `experiments[].parameters` |
| `claim_evidence_plan.json` (from 07) | `claims[].id`, `claims[].pass_criteria` |

**Output (per experiment `experiments/<task_id>/`):**

| File | Key Fields |
|------|------------|
| `config/experiment_config.json` | Experiment configuration |
| `config/hyperparameters.json` | Hyperparameter values |
| `raw_results/results.json` | Raw experiment results, `data_origin` (**must be `real`**) |
| `processed_results/metrics.json` | Computed metrics, `data_origin` (**must be `real`**) |
| `provenance/execution_log.json` | `adapter_used`, `adapter_version`, `data_origin`, `environment`, `git_commit` |
| `environment/requirements.txt` | Environment requirements |
| `environment/python_version` | Python version used |
| `environment/os_info` | OS information |

**Dependencies:** Upstream: 06, 07. Downstream: 10, 11.

---

## Module 10 — Result Analysis

**Function:** Analyzes results from synthetic and real experiments against the claim-evidence plan, producing scientific analysis, claim-evidence mapping, revision recommendations, and a routing decision.

**Input:**

| File | Key Fields |
|------|------------|
| `synthetic_results/metrics.csv` (from 08) | `experiment_id`, `metric_name`, `metric_value` |
| `synthetic_results/statistics.json` (from 08) | `experiment_id`, `summary_stats` |
| `experiments/<task_id>/processed_results/metrics.json` (from 09, optional) | Computed metrics |
| `experiments/<task_id>/raw_results/results.json` (from 09, optional) | Raw results |
| `claim_evidence_plan.json` (from 07) | `claims[].id`, `claims[].statement`, `claims[].pass_criteria` |

**Output:**

| File | Key Fields |
|------|------------|
| `decision.json` | `decision` (one of: `PASS_TO_FIGURE_TABLE`, `RETURN_TO_EXPERIMENT`, `RETURN_TO_EXPERIMENT_PLAN`, `RETURN_TO_METHOD`, `RETURN_TO_INNOVATION`, `HUMAN_REVIEW_REQUIRED`), `reasoning`, `claims_passed`, `claims_failed`, `claims_inconclusive`, `target_module` |
| `claim_evidence_mapping.md` | `mappings[].claim_id`, `mappings[].claim_statement`, `mappings[].evidence`, `mappings[].verdict` (pass/fail/inconclusive), `mappings[].data_origin` |

**Dependencies:** Upstream: 07, 08, 09. Downstream: 11 (or loops back to 05/06/07/09).

---

## Module 11 — Figure & Table Generation

**Function:** Generates publication-quality figures and tables from experiment results, method specs, and external data. Supports external data with `data_origin='external'`.

**Input:**

| File | Key Fields |
|------|------------|
| `method_spec.json` (from 06) | `method_name`, `components` |
| `paper_figure_plan.yaml` (from 07) | `figures[].id`, `figures[].type`, `figures[].data_source`, `tables[].id`, `tables[].data_source` |

**Output:**

| File | Key Fields |
|------|------------|
| `figures/*.svg` | `figure_id`, `data_origin` (synthetic/real/external), `vector_format` (**must be True**) |
| `figures/source_data/` | `data_files`, `data_origin` |
| `figures/plotting_specs/` | `spec_files`, `spec_format` |
| `tables/*.xlsx` | `table_id`, `data_origin` (synthetic/real/external) |
| `captions/captions.yaml` | `captions[].id`, `captions[].caption`, `captions[].type` (figure/table) |

**Dependencies:** Upstream: 06, 07, 08, 09, external. Downstream: 12.

---

## Module 12 — Paper Writing

**Function:** Writes the full research paper in three formats: Markdown, LaTeX, and Word. Integrates all upstream outputs into a coherent manuscript.

**Input:**

| File | Key Fields |
|------|------------|
| `figures/` (from 11) | `svg_files`, `pdf_files` |
| `captions/captions.yaml` (from 11) | Caption data |
| `tables/` (from 11) | `xlsx_files`, `csv_files`, `tex_files` |
| `paper_style_profile.json` (optional) | `venue`, `style` (default: ieee), `page_limit`, `citation_style` (default: numeric) |

**Output:**

| File | Key Fields |
|------|------------|
| `paper/paper.md` | `title`, `abstract`, `sections[].heading`, `sections[].content`, `figure_references`, `table_references` |
| `paper/latex/main.tex` | LaTeX source |
| `paper/latex/references.bib` | BibTeX (optional) |
| `paper/latex/figures/` | Figure files for LaTeX |
| `paper/word/paper.docx` | Word document |
| `paper/word/embedded_figures` | Embedded figure list |

**Dependencies:** Upstream: all. Downstream: 13.

---

## Module 13 — Reference & Supplementary

**Function:** Generates the bibliography file, validates citations against paper metadata, and produces supplementary materials in LaTeX and Word formats. This is the final module.

**Input:**

| File | Key Fields |
|------|------------|
| `paper/paper.md` (from 12) | Paper content |
| `paper/latex/` (from 12) | LaTeX directory |
| `paper/word/` (from 12, optional) | Word directory |
| `paper_metadata.jsonl` (from 01) | `paper_id`, `title`, `authors`, `year`, `doi` |

**Output:**

| File | Key Fields |
|------|------------|
| `references.bib` | `entries[].key`, `entries[].type`, `entries[].title`, `entries[].author`, `entries[].year` |
| `citation_validation_report.md` | `total_citations`, `valid_citations`, `invalid_citations`, `missing_metadata`, `issues` |
| `supplementary.tex` | `content`, `sections`, `compilable` (**must be True**) |
| `supplementary.docx` | `content`, `sections` |

**Dependencies:** Upstream: 01, 12. Downstream: none (terminal module).

---

## Running Individual Modules

Modules are normally run via the CLI through the Orchestrator. To run a single module:

```powershell
# Rerun from a specific module (uses existing upstream outputs):
python -m Research_Agent_v3.cli.cli rerun --task my_task.yaml --from 10
```

**To run a module completely standalone (advanced):**
1. Prepare all input files in the expected directory structure
2. Ensure all config files (`configs/*.yaml`) are correctly set
3. Use `rerun --from <MODULE_ID>` to start from that module

**Required inputs for standalone module runs:**

| Module | What You Must Prepare |
|--------|---------------------|
| 01 | `research_task.yaml` with research_question, keywords, domain |
| 02 | `download_queue.json` from Module 01 output |
| 03 | `papers/<paper_id>/normalized/paper.md` from Module 02 output |
| 04 | `paper_analysis.json` from Module 03 output |
| 05 | `gap_candidates.json` from 04 + `paper_analysis.json` from 03 |
| 06 | `final_research_direction.md` from Module 05 output |
| 07 | `method_spec.json` from Module 06 output |
| 08 | `method_spec.json` (06) + `experiment_matrix.yaml` (07) + `claim_evidence_plan.json` (07) |
| 09 | Same as 08 (but experiments with `data_origin=real`) |
| 10 | `synthetic_results/` (08) + `experiments/` (09) + `claim_evidence_plan.json` (07) |
| 11 | `method_spec.json` (06) + `paper_figure_plan.yaml` (07) + experiment results |
| 12 | `figures/` (11) + `tables/` (11) + `captions/captions.yaml` (11) |
| 13 | `paper/paper.md` (12) + `paper_metadata.jsonl` (01) |

---

## Module Lifecycle (All Modules)

Every module follows the same 7-method lifecycle:

1. `load_config()` — Load module-specific configuration
2. `validate_input()` — Validate input files against schema
3. `execute()` — Run the module's core logic
4. `validate_output()` — Validate output files against schema
5. `quality_assessment()` — Run quality checks
6. `write_manifest()` — Write module manifest
7. `write_report()` — Write module report

If any step fails, the module raises an error and the pipeline state is saved for resume.

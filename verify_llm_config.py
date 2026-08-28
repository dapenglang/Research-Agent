"""Verify dual-model LLM configuration before running the pipeline."""
import sys
sys.path.insert(0, r"D:\Research Agent")
sys.path.insert(0, r"D:\Research Agent\Research_Agent_v3")

from Research_Agent_v3.infrastructure.llm_runtime.runtime import LLMRuntime
from Research_Agent_v3.infrastructure.llm.llm_provider import MockProvider

runtime = LLMRuntime(r"D:\Research Agent\Research_Agent_v3\configs")
runtime.load()

print("=" * 60)
print("LLM Configuration Verification")
print("=" * 60)

task_types = [
    "literature_analysis",
    "innovation_reasoning",
    "method_design",
    "experiment_analysis",
    "reviewer",
    "paper_generation",
    "figure_generation",
    "reference_checking",
]

all_ok = True
for task in task_types:
    provider = runtime.get_provider(task)
    if provider is None:
        print(f"  [FAIL] {task}: No provider available")
        all_ok = False
    elif isinstance(provider, MockProvider):
        print(f"  [FAIL] {task}: Mock provider detected (NOT allowed)")
        all_ok = False
    elif not provider.is_available():
        print(f"  [FAIL] {task}: Provider not available - {provider.get_name()}")
        all_ok = False
    else:
        print(f"  [ OK ] {task}: {provider.get_name()}")

print("=" * 60)
if all_ok:
    print("All LLM providers configured correctly!")
else:
    print("Some providers failed - check configuration.")

# Quick test call
print("\nQuick test call to deepseek-r1:8b...")
provider = runtime.get_provider("innovation_reasoning")
if provider and provider.is_available():
    try:
        result = provider.generate("What is 2+2? Answer in one word.", max_tokens=10)
        print(f"  Response: {result[:100]}")
    except Exception as e:
        print(f"  Test call failed: {e}")

print("\nQuick test call to gemma4:26b...")
provider = runtime.get_provider("paper_generation")
if provider and provider.is_available():
    try:
        result = provider.generate("What is 2+2? Answer in one word.", max_tokens=10)
        print(f"  Response: {result[:100]}")
    except Exception as e:
        print(f"  Test call failed: {e}")

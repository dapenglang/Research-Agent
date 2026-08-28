"""Test both models with proper max_tokens for thinking models."""
import sys
sys.path.insert(0, r"D:\Research Agent")
sys.path.insert(0, r"D:\Research Agent\Research_Agent_v3")

from Research_Agent_v3.infrastructure.llm_runtime.runtime import LLMRuntime

runtime = LLMRuntime(r"D:\Research Agent\Research_Agent_v3\configs")
runtime.load()

# Test gemma4:26b with higher max_tokens
print("Testing gemma4:26b with max_tokens=4096...")
provider = runtime.get_provider("paper_generation")
if provider and provider.is_available():
    try:
        result = provider.generate(
            "Write a 2-sentence abstract about adversarial defense for vision-language models.",
            max_tokens=4096,
        )
        print(f"  Status: SUCCESS")
        print(f"  Response length: {len(result)} chars")
        if len(result) > 0:
            print(f"  Preview: {result[:500]}")
        else:
            print(f"  Empty response - thinking may have consumed all tokens")
    except Exception as e:
        print(f"  Status: FAILED - {e}")

print()

# Test deepseek-r1:8b
print("Testing deepseek-r1:8b with max_tokens=4096...")
provider = runtime.get_provider("innovation_reasoning")
if provider and provider.is_available():
    try:
        result = provider.generate(
            "Write a 2-sentence abstract about adversarial defense for vision-language models.",
            max_tokens=4096,
        )
        print(f"  Status: SUCCESS")
        print(f"  Response length: {len(result)} chars")
        print(f"  Preview: {result[:500]}")
    except Exception as e:
        print(f"  Status: FAILED - {e}")

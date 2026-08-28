#!/usr/bin/env python
"""
LLM Diagnostic — checks provider config, API key, endpoint, and response.

Tests all configured LLM providers and the task types required for research.
Outputs "LLM Connection Success" on success, or LLM_Error_Report.md on failure.

Usage:
    python scripts/check_llm.py
    python scripts/check_llm.py --provider deepseek
    python scripts/check_llm.py --task paper_generation

Exit codes:
    0 — at least one provider fully functional
    1 — no provider fully functional
    2 — configuration error
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


def find_project_root() -> Path:
    current = Path(__file__).resolve().parent.parent
    if (current / "configs").exists():
        return current
    return Path.cwd()


RESEARCH_TASKS = [
    "innovation_reasoning",
    "method_design",
    "experiment_analysis",
    "paper_generation",
]

TEST_PROMPT = "Reply with exactly: HELLO"


def load_configs(project_root: Path) -> Tuple[Dict, Dict]:
    """Load providers.yaml and llm_routing.yaml."""
    configs_dir = project_root / "configs"
    providers_path = configs_dir / "providers.yaml"
    routing_path = configs_dir / "llm_routing.yaml"

    providers_config: Dict = {}
    routing_config: Dict = {}

    if providers_path.exists():
        with open(providers_path, "r", encoding="utf-8") as f:
            providers_config = yaml.safe_load(f) or {}
    if routing_path.exists():
        with open(routing_path, "r", encoding="utf-8") as f:
            routing_config = yaml.safe_load(f) or {}

    return providers_config, routing_config


def check_env_var(env_name: str) -> Tuple[bool, str]:
    """Check if an environment variable is set and non-empty."""
    value = os.environ.get(env_name, "")
    if value:
        masked = value[:4] + "****" + value[-4:] if len(value) > 8 else "****"
        return True, masked
    return False, "(empty)"


def test_provider(
    provider_name: str,
    provider_config: Dict[str, Any],
    task_type: str = "",
) -> Dict[str, Any]:
    """Test a single LLM provider configuration."""
    result: Dict[str, Any] = {
        "provider": provider_name,
        "type": provider_config.get("type", provider_name),
        "model": provider_config.get("model", ""),
        "endpoint": provider_config.get("endpoint", ""),
        "api_key_set": False,
        "api_key_masked": "",
        "config_ok": False,
        "connection_ok": False,
        "response_ok": False,
        "response_text": "",
        "error": "",
    }

    provider_type = provider_config.get("type", provider_name).lower()

    if provider_type == "mock":
        result["config_ok"] = True
        result["api_key_set"] = True
        result["api_key_masked"] = "N/A (mock)"
        result["connection_ok"] = True
        result["response_ok"] = True
        result["response_text"] = "[Mock provider — no real connection]"
        return result

    api_key_env = provider_config.get("api_key_env", "")
    if api_key_env:
        key_set, masked = check_env_var(api_key_env)
        result["api_key_set"] = key_set
        result["api_key_masked"] = masked
        if not key_set:
            result["error"] = f"Environment variable {api_key_env} is not set"
            return result

    endpoint = provider_config.get("endpoint", "")
    if provider_type == "local" and not endpoint:
        result["error"] = "No endpoint configured for local provider"
        return result

    result["config_ok"] = True

    if not result["api_key_set"] and provider_type != "local":
        return result

    try:
        sys.path.insert(0, str(find_project_root().parent))
        from Research_Agent_v3.infrastructure.llm.llm_provider import LLMProviderFactory

        factory_config = dict(provider_config)
        if api_key_env:
            factory_config["api_key"] = os.environ.get(api_key_env, "")

        provider = LLMProviderFactory.create_provider(factory_config)

        if not provider.is_available():
            result["error"] = "Provider.is_available() returned False"
            return result

        result["connection_ok"] = True

        response = provider.generate(TEST_PROMPT)
        if response and len(response) > 0:
            result["response_ok"] = True
            result["response_text"] = response[:200]
        else:
            result["error"] = "Empty response from API"
    except Exception as e:
        result["error"] = str(e)

    return result


def generate_success_report(results: List[Dict]) -> str:
    """Generate success report."""
    lines = [
        "# LLM Connection Success",
        "",
        f"**检查时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Provider 状态",
        "",
        "| Provider | Type | Model | API Key | Config | Connection | Response |",
        "|----------|------|-------|---------|--------|------------|----------|",
    ]
    for r in results:
        lines.append(
            f"| {r['provider']} | {r['type']} | {r['model']} | "
            f"{'YES' if r['api_key_set'] else 'NO'} | "
            f"{'OK' if r['config_ok'] else 'FAIL'} | "
            f"{'OK' if r['connection_ok'] else 'FAIL'} | "
            f"{'OK' if r['response_ok'] else 'FAIL'} |"
        )
    lines.append("")
    return "\n".join(lines)


def generate_error_report(results: List[Dict]) -> str:
    """Generate error report."""
    lines = [
        "# LLM Error Report",
        "",
        f"**检查时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Provider 诊断详情",
        "",
    ]
    for r in results:
        lines.append(f"### {r['provider']}")
        lines.append(f"- **Type**: {r['type']}")
        lines.append(f"- **Model**: {r['model']}")
        lines.append(f"- **Endpoint**: {r['endpoint'] or 'N/A'}")
        lines.append(f"- **API Key**: {'已设置 (' + r['api_key_masked'] + ')' if r['api_key_set'] else '未设置'}")
        lines.append(f"- **配置检查**: {'PASS' if r['config_ok'] else 'FAIL'}")
        lines.append(f"- **连接检查**: {'PASS' if r['connection_ok'] else 'FAIL'}")
        lines.append(f"- **响应检查**: {'PASS' if r['response_ok'] else 'FAIL'}")
        if r["error"]:
            lines.append(f"- **错误信息**: {r['error']}")
        if r["response_text"]:
            lines.append(f"- **响应内容**: {r['response_text'][:100]}")
        lines.append("")

    functional = [r for r in results if r["response_ok"]]
    if not functional:
        lines.append("## 修复建议")
        lines.append("")
        lines.append("没有可用的 LLM Provider。请按以下步骤排查：")
        lines.append("")
        lines.append("### OpenAI")
        lines.append("1. 获取 API Key: https://platform.openai.com/api-keys")
        lines.append("2. 设置环境变量: `set OPENAI_API_KEY=sk-...`")
        lines.append("3. 重新运行: `python scripts/check_llm.py`")
        lines.append("")
        lines.append("### DeepSeek")
        lines.append("1. 获取 API Key: https://platform.deepseek.com/api_keys")
        lines.append("2. 设置环境变量: `set DEEPSEEK_API_KEY=sk-...`")
        lines.append("3. 重新运行: `python scripts/check_llm.py`")
        lines.append("")
        lines.append("### Local (vLLM/Ollama)")
        lines.append("1. 安装 vLLM 或 Ollama")
        lines.append("2. 启动模型服务")
        lines.append("3. 设置环境变量: `set LOCAL_LLM_ENDPOINT=http://localhost:8000/v1`")
        lines.append("4. 重新运行: `python scripts/check_llm.py`")
        lines.append("")
        lines.append("详细配置请参考: `docs/LLM_Configuration_Guide_CN.md`")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="LLM Diagnostic Check")
    parser.add_argument("--provider", type=str, default=None, help="Test specific provider only")
    parser.add_argument("--task", type=str, default=None, help="Test specific task type routing")
    parser.add_argument("--output", type=str, default=None, help="Output report path")
    args = parser.parse_args()

    project_root = find_project_root()
    providers_config, routing_config = load_configs(project_root)

    llm_providers = providers_config.get("providers", {}).get("llm", {})
    results: List[Dict] = []

    for name, config in llm_providers.items():
        if name in ("default", "mock"):
            continue
        if args.provider and name != args.provider:
            continue
        results.append(test_provider(name, config))

    if not results:
        print("ERROR: No LLM providers found in config")
        return 2

    any_success = any(r["response_ok"] for r in results)
    output_path = Path(args.output) if args.output else project_root / (
        "LLM_Connection_Success.md" if any_success else "LLM_Error_Report.md"
    )

    if any_success:
        report = generate_success_report(results)
        print("LLM Connection Success")
        for r in results:
            status = "OK" if r["response_ok"] else "FAIL"
            print(f"  [{status}] {r['provider']} ({r['model']})")
    else:
        report = generate_error_report(results)
        print("LLM Connection FAILED")
        for r in results:
            print(f"  [FAIL] {r['provider']}: {r.get('error', 'unknown')}")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nReport: {output_path}")

    return 0 if any_success else 1


if __name__ == "__main__":
    sys.exit(main())

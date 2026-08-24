# LLM Provider Guide — Research Agent v3

**Date:** 2026-08-15
**Verified from:** `infrastructure/llm/llm_provider.py`, `configs/providers.yaml`

---

## 1. Overview

Research Agent v3 provides three LLM provider types:

| Provider | Class | Status | Use Case |
|----------|-------|--------|----------|
| OpenAI | `OpenAIProvider` | Implemented | Production research (requires API key) |
| Local | `LocalLLMProvider` | Implemented | Production research with local LLM (vLLM, Ollama) |
| Mock | `MockProvider` | Implemented | Testing/development ONLY |

---

## 2. Provider Details

### 2.1 OpenAI Provider

**Class:** `OpenAIProvider` (extends `LLMProvider`)
**Status:** Fully implemented — makes real OpenAI API calls

**Configuration (`configs/providers.yaml`):**
```yaml
providers:
  llm:
    default: "openai"
    openai:
      api_key_env: "OPENAI_API_KEY"    # Environment variable name
      model: "gpt-4"                    # Model name
      temperature: 0.3                  # Sampling temperature
      max_tokens: 4096                  # Max tokens per call
```

**Setup:**
```powershell
# Set API key as environment variable
$env:OPENAI_API_KEY = "sk-your-key-here"

# Or permanently:
[System.Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "sk-your-key-here", "User")
```

**Usage:**
```python
from Research_Agent_v3.infrastructure.llm.llm_provider import LLMProviderFactory

factory = LLMProviderFactory()
provider = factory.create("openai")
result = provider.generate("Summarize this paper: ...")
```

### 2.2 Local LLM Provider

**Class:** `LocalLLMProvider` (extends `LLMProvider`)
**Status:** Fully implemented — makes HTTP calls to a local LLM endpoint

**Configuration:**
```yaml
providers:
  llm:
    default: "local"
    local:
      endpoint: "http://localhost:8000/v1"
      model: "llama-3-8b"
```

**Supported backends:**
- vLLM (recommended for GPU)
- Ollama (for CPU)
- Any OpenAI-compatible API server

**Setup (vLLM example):**
```powershell
# Install vLLM
pip install vllm

# Start a local LLM server
python -m vllm.entrypoints.openai.api_server --model meta-llama/Llama-3-8B --port 8000
```

### 2.3 Mock Provider

**Class:** `MockProvider` (extends `LLMProvider`)
**Status:** Fully implemented — template-based responses

**CRITICAL RULES:**

Mock is **ONLY allowed** for:
- `unit_test`
- `integration_test`
- `development`

Mock is **PROHIBITED** for:
- `literature_analysis`
- `innovation_generation`
- `paper_generation`
- `experiment_analysis`

**Enforcement:** The `validate_usage(provider_name, task_type)` function checks these rules at runtime. If a prohibited combination is detected, it logs an error and returns `False`.

**Configuration:**
```yaml
providers:
  llm:
    mock:
      only_for:
        - unit_test
        - integration_test
        - development
      prohibited_for:
        - literature_analysis
        - innovation_generation
        - paper_generation
        - experiment_analysis
```

---

## 3. Provider Selection

### 3.1 For Production Research

Use **OpenAI** or **Local** provider:
```yaml
# In research_task.yaml:
llm:
  type: "openai"    # or "local"
```

### 3.2 For Testing/Development

Use **Mock** provider:
```yaml
# In research_task.yaml:
llm:
  type: "mock"
```

### 3.3 If No Real Provider Is Configured

If you attempt to use a production task (e.g., `literature_analysis`) without a real provider:
- The system will return: `BLOCKED` or `NOT_CONFIGURED`
- It will **NOT** fall back to mock automatically
- You must configure a real provider (OpenAI or Local)

---

## 4. Validation API

```python
from Research_Agent_v3.infrastructure.llm.llm_provider import validate_usage

# Check if a provider is allowed for a task
is_allowed = validate_usage("mock", "literature_analysis")  # Returns False
is_allowed = validate_usage("openai", "literature_analysis")  # Returns True
is_allowed = validate_usage("mock", "unit_test")  # Returns True
```

---

## 5. Provider Factory

```python
from Research_Agent_v3.infrastructure.llm.llm_provider import LLMProviderFactory

factory = LLMProviderFactory()

# Create by name
provider = factory.create("openai")
provider = factory.create("local")
provider = factory.create("mock")

# Check availability
if provider.is_available():
    result = provider.generate(prompt)
```

---

## 6. MCP Integration

MCP is **optional** and is **NOT** a hard dependency of the Research Agent pipeline.

```yaml
providers:
  mcp:
    enabled: false    # Set to true to enable MCP
    servers: []       # List of MCP server configs
```

If MCP is disabled, the pipeline runs normally without it. MCP can enhance but never block the core pipeline.

---

## 7. Windows-Specific Notes

### 7.1 Setting Environment Variables

```powershell
# Temporary (current session):
$env:OPENAI_API_KEY = "sk-your-key-here"

# Permanent (user-level):
[System.Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "sk-your-key-here", "User")

# Verify:
echo $env:OPENAI_API_KEY
```

### 7.2 Local LLM on Windows

For local LLM on Windows with RTX A500:
- vLLM may have limited Windows support; consider using WSL2
- Ollama has native Windows support and is easier to set up
- Ensure the endpoint URL is correct in `providers.yaml`

### 7.3 Network Proxy

If behind a corporate proxy, set in `configs/machine.yaml`:
```yaml
machine:
  network:
    proxy: "http://proxy.company.com:8080"
```

And set environment variables:
```powershell
$env:HTTP_PROXY = "http://proxy.company.com:8080"
$env:HTTPS_PROXY = "http://proxy.company.com:8080"
```

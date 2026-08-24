# LLM 配置指南

> 本文档详细说明如何配置 OpenAI、DeepSeek 和本地模型作为 Research Agent 的 LLM 后端。

---

## 目录

1. [配置文件概览](#1-配置文件概览)
2. [OpenAI 配置](#2-openai-配置)
3. [DeepSeek 配置](#3-deepseek-配置)
4. [本地模型配置](#4-本地模型配置)
5. [任务路由](#5-任务路由)
6. [测试与诊断](#6-测试与诊断)
7. [常见错误](#7-常见错误)

---

## 1. 配置文件概览

Research Agent 使用两个配置文件管理 LLM：

| 文件 | 用途 |
|------|------|
| `configs/providers.yaml` | 定义所有 LLM 提供商的连接参数 |
| `configs/llm_routing.yaml` | 将研究任务路由到不同的 LLM 提供商 |

### providers.yaml 结构

```yaml
providers:
  llm:
    openai:       # OpenAI 提供商
      type: "openai"
      model: "gpt-4"
      api_key_env: "OPENAI_API_KEY"    # 从环境变量读取
      temperature: 0.3
      max_tokens: 4096

    deepseek:     # DeepSeek 提供商
      type: "deepseek"
      model: "deepseek-chat"
      api_key_env: "DEEPSEEK_API_KEY"
      endpoint: "https://api.deepseek.com/v1"
      temperature: 0.3
      max_tokens: 4096

    local:        # 本地模型提供商
      type: "local"
      backend: "vllm"
      model: "Qwen2.5-7B-Instruct"
      endpoint: "http://localhost:8000/v1"
      temperature: 0.3
      max_tokens: 4096
```

---

## 2. OpenAI 配置

### 2.1 获取 API Key

1. 访问 https://platform.openai.com/api-keys
2. 登录 OpenAI 账号（无账号需先注册）
3. 点击 "Create new secret key"
4. 复制 Key（格式: `sk-...`）

### 2.2 设置环境变量

**Windows (PowerShell):**
```powershell
# 临时设置（当前会话有效）
$env:OPENAI_API_KEY = "sk-你的密钥"

# 永久设置
[System.Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "sk-你的密钥", "User")
```

**Windows (CMD):**
```cmd
set OPENAI_API_KEY=sk-你的密钥
```

**Linux/Mac:**
```bash
export OPENAI_API_KEY="sk-你的密钥"
# 永久设置: 添加到 ~/.bashrc 或 ~/.zshrc
```

### 2.3 providers.yaml 配置

默认配置已包含 OpenAI，通常无需修改。如需自定义：

```yaml
providers:
  llm:
    openai:
      type: "openai"
      model: "gpt-4"              # 可选: gpt-4, gpt-4-turbo, gpt-3.5-turbo
      api_key_env: "OPENAI_API_KEY"
      temperature: 0.3
      max_tokens: 4096
      # 如使用 Azure OpenAI 或代理:
      # endpoint: "https://your-proxy.com/v1"
```

### 2.4 测试方法

```bash
python scripts/check_llm.py --provider openai
```

成功输出:
```
LLM Connection Success
  [OK] openai (gpt-4)
```

### 2.5 常见错误

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `API key not configured` | 环境变量未设置 | `set OPENAI_API_KEY=sk-...` |
| `openai package not installed` | 缺少 openai 包 | `pip install openai` |
| `Incorrect API key provided` | Key 无效或过期 | 重新生成 API Key |
| `Rate limit reached` | 调用频率超限 | 降低调用频率或升级套餐 |
| `quota exceeded` | 额度用完 | 充值或更换提供商 |

---

## 3. DeepSeek 配置

### 3.1 获取 API Key

1. 访问 https://platform.deepseek.com/api_keys
2. 注册/登录 DeepSeek 账号
3. 点击 "Create API Key"
4. 复制 Key（格式: `sk-...`）

### 3.2 设置环境变量

**Windows (PowerShell):**
```powershell
$env:DEEPSEEK_API_KEY = "sk-你的密钥"
```

**Windows (CMD):**
```cmd
set DEEPSEEK_API_KEY=sk-你的密钥
```

**Linux/Mac:**
```bash
export DEEPSEEK_API_KEY="sk-你的密钥"
```

### 3.3 endpoint 配置

DeepSeek 使用 OpenAI 兼容接口，默认 endpoint:
```
https://api.deepseek.com/v1
```

无需修改，`providers.yaml` 已包含此配置。

### 3.4 model 配置

DeepSeek 支持的模型:

| 模型 | 说明 | 适用场景 |
|------|------|---------|
| `deepseek-chat` | 通用对话模型 | 文献分析、结果分析、论文生成 |
| `deepseek-reasoner` | 推理增强模型 | 创新推理、方法设计 |

修改 `providers.yaml`:
```yaml
deepseek:
  type: "deepseek"
  model: "deepseek-chat"       # 或 "deepseek-reasoner"
  api_key_env: "DEEPSEEK_API_KEY"
  endpoint: "https://api.deepseek.com/v1"
  temperature: 0.3
  max_tokens: 4096
```

### 3.5 测试方法

```bash
python scripts/check_llm.py --provider deepseek
```

成功输出:
```
LLM Connection Success
  [OK] deepseek (deepseek-chat)
```

### 3.6 常见错误

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `API key not configured` | 环境变量未设置 | `set DEEPSEEK_API_KEY=sk-...` |
| `Authentication Fails` | Key 无效 | 重新生成 Key |
| `Insufficient Balance` | 余额不足 | 充值 DeepSeek 账户 |
| `Connection timeout` | 网络问题 | 检查网络连接 |

---

## 4. 本地模型配置

### 4.1 使用 vLLM

**安装 vLLM:**
```bash
pip install vllm
```

**启动模型服务:**
```bash
# 启动 Qwen2.5-7B
python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-7B-Instruct \
    --port 8000

# 启动 Llama 3
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Meta-Llama-3-8B-Instruct \
    --port 8000
```

**设置环境变量:**
```bash
set LOCAL_LLM_ENDPOINT=http://localhost:8000/v1
```

### 4.2 使用 Ollama

**安装 Ollama:**
```bash
# 访问 https://ollama.ai 下载安装
```

**拉取模型:**
```bash
ollama pull qwen2.5:7b
# 或
ollama pull llama3:8b
```

**启动服务:**
```bash
ollama serve
```

**设置环境变量:**
```bash
set LOCAL_LLM_ENDPOINT=http://localhost:11434/v1
```

### 4.3 providers.yaml 配置

```yaml
local:
  type: "local"
  backend: "vllm"                    # 或 "ollama"
  model: "Qwen2.5-7B-Instruct"       # 模型名称
  model_path: "/data/models/Qwen"    # 模型路径（可选）
  endpoint: "http://localhost:8000/v1"
  temperature: 0.3
  max_tokens: 4096
```

### 4.4 测试方法

```bash
python scripts/check_llm.py --provider local
```

### 4.5 常见错误

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `Connection refused` | 服务未启动 | 启动 vLLM/Ollama 服务 |
| `Model not found` | 模型名称错误 | 检查模型名称拼写 |
| `CUDA out of memory` | GPU 内存不足 | 使用更小模型或减少 batch size |
| `requests package not installed` | 缺少 requests | `pip install requests` |

---

## 5. 任务路由

`configs/llm_routing.yaml` 将不同研究任务路由到不同模型：

```yaml
routing:
  literature_analysis:       # 文献分析
    provider: "deepseek"
    model: "deepseek-chat"
    temperature: 0.2         # 低温度 = 更精确

  innovation_reasoning:      # 创新推理
    provider: "openai"
    model: "gpt-4"
    temperature: 0.5         # 高温度 = 更有创意

  method_design:             # 方法设计
    provider: "openai"
    model: "gpt-4"
    temperature: 0.3

  experiment_analysis:       # 实验分析
    provider: "deepseek"
    model: "deepseek-chat"
    temperature: 0.2

  paper_generation:          # 论文生成
    provider: "openai"
    model: "gpt-4"
    temperature: 0.7         # 最高温度 = 最有创造性

default:                     # 默认回退
  provider: "deepseek"
  model: "deepseek-chat"
  temperature: 0.3
```

### 自定义路由

如果你只有 DeepSeek，可以将所有任务路由到 DeepSeek：

```yaml
routing:
  literature_analysis:
    provider: "deepseek"
    model: "deepseek-chat"
    temperature: 0.2
  innovation_reasoning:
    provider: "deepseek"
    model: "deepseek-reasoner"
    temperature: 0.5
  method_design:
    provider: "deepseek"
    model: "deepseek-chat"
    temperature: 0.3
  experiment_analysis:
    provider: "deepseek"
    model: "deepseek-chat"
    temperature: 0.2
  paper_generation:
    provider: "deepseek"
    model: "deepseek-chat"
    temperature: 0.7

default:
  provider: "deepseek"
  model: "deepseek-chat"
  temperature: 0.3
```

---

## 6. 测试与诊断

### 6.1 快速检查

```bash
# 检查所有提供商
python scripts/check_llm.py

# 检查特定提供商
python scripts/check_llm.py --provider deepseek

# 完整就绪检查
python scripts/check_research_ready.py
```

### 6.2 Python 代码测试

```python
from Research_Agent_v3.infrastructure.llm_runtime.runtime import LLMRuntime

runtime = LLMRuntime()
runtime.load()

# 检查所有提供商状态
status = runtime.get_status()
print(status)

# 获取特定任务的提供商
provider = runtime.get_provider("paper_generation")
if provider:
    response = provider.generate("写一段关于视觉语言模型安全性的摘要")
    print(response)
else:
    print("No provider available for paper_generation")
```

---

## 7. 常见错误

### 7.1 Mock Provider 限制

Mock Provider 仅用于开发和测试，**禁止**用于以下任务：
- `literature_analysis` (文献分析)
- `innovation_generation` (创新生成)
- `paper_generation` (论文生成)
- `experiment_analysis` (实验分析)

如果尝试在这些任务中使用 Mock，`validate_usage()` 会返回 `False`。

### 7.2 API Key 泄露防护

- API Key 通过环境变量传递，不写入代码或配置文件
- `providers.yaml` 中使用 `api_key_env` 字段引用环境变量名
- 日志中不会打印完整 API Key

### 7.3 网络问题

如果在中国大陆访问 OpenAI API 有网络问题：
1. 使用 DeepSeek 替代（国内访问无需代理）
2. 或使用本地模型
3. 或配置 HTTP 代理

### 7.4 多提供商混合使用

可以同时配置多个提供商，系统会根据 `llm_routing.yaml` 自动选择：

```bash
# 同时设置两个 Key
set OPENAI_API_KEY=sk-xxx
set DEEPSEEK_API_KEY=sk-yyy

# 系统会自动路由:
# - 文献分析 -> DeepSeek (低成本)
# - 创新推理 -> OpenAI (高质量)
# - 论文生成 -> OpenAI (高质量)
```

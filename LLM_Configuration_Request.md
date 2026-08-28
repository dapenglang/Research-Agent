# LLM Configuration Request

## 当前状态

| LLM 提供商 | 状态 | 说明 |
|-----------|------|------|
| Ollama (deepseek-r1:8b) | ❌ 未运行 | 本地服务 http://localhost:11434 无法连接 |
| Ollama (gemma4:26b) | ❌ 未运行 | 同上 |
| OpenAI API | ❌ 未配置 | 环境变量 OPENAI_API_KEY 未设置 |
| DeepSeek API | ❌ 未配置 | 环境变量 DEEPSEEK_API_KEY 未设置 |

## 影响

以下模块**必须使用真实 LLM**（项目约束：禁止 Mock LLM 用于科研任务）：

| 模块 | LLM 用途 | 当前状态 |
|------|---------|---------|
| Module 03 | 文献智能分析 | 无法正常运行 |
| Module 04 | 研究领域全景分析 | 无法正常运行 |
| Module 05 | 创新发现 | 无法正常运行 |
| Module 06 | 方法设计 | 无法正常运行 |
| Module 07 | 实验规划 | 无法正常运行 |
| Module 10 | 结果分析 | 无法正常运行 |
| Module 12 | 论文写作 | 无法正常运行 |
| Module 14 | 审稿模拟 | 无法正常运行 |

## 配置方式

### 方案 A: 启动 Ollama（推荐，无需 API 密钥）

1. 安装 Ollama: https://ollama.com/download
2. 下载模型:
```bash
ollama pull deepseek-r1:8b
ollama pull gemma4:26b
```
3. 启动服务:
```bash
ollama serve
```
4. 验证连接:
```bash
curl http://localhost:11434/api/tags
```

### 方案 B: 配置 DeepSeek API

1. 获取 API Key: https://platform.deepseek.com/
2. 设置环境变量:
```powershell
$env:DEEPSEEK_API_KEY = "your-api-key-here"
```
3. 修改 `configs/llm.yaml` 中 `provider: deepseek`

### 方案 C: 配置 OpenAI API

1. 获取 API Key: https://platform.openai.com/api-keys
2. 设置环境变量:
```powershell
$env:OPENAI_API_KEY = "your-api-key-here"
```
3. 修改 `configs/llm.yaml` 中 `provider: openai`

## 配置文件位置

| 文件 | 路径 | 说明 |
|------|------|------|
| LLM 主配置 | `configs/llm.yaml` | 提供商、模型、路由配置 |
| 提供商配置 | `configs/providers.yaml` | 提供商详细参数 |
| 依赖策略 | `configs/dependency_policy.yaml` | LLM 失败时的回退策略 |

## 测试方法

配置完成后，运行:
```bash
conda activate research_agent_v3
python scripts/check_llm.py
```

或直接运行 Pipeline:
```bash
python run_vlm_safety.py
```

## 当前 Pipeline 状态

上次成功运行时间: 2026-08-17（Ollama 可用时）
- Module 04 使用 deepseek-r1:8b 完成了研究空白分析
- Module 12 使用 gemma4:26b 生成了论文（耗时17分钟）
- 当前重新运行需要 LLM 支持

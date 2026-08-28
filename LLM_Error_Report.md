# LLM Error Report

**检查时间**: 2026-08-17 02:34:00

## Provider 诊断详情

### openai
- **Type**: openai
- **Model**: gpt-4o
- **Endpoint**: https://api.openai.com/v1
- **API Key**: 未设置
- **配置检查**: FAIL
- **连接检查**: FAIL
- **响应检查**: FAIL
- **错误信息**: Environment variable OPENAI_API_KEY is not set

### deepseek
- **Type**: deepseek
- **Model**: deepseek-reasoner
- **Endpoint**: https://api.deepseek.com/v1
- **API Key**: 未设置
- **配置检查**: FAIL
- **连接检查**: FAIL
- **响应检查**: FAIL
- **错误信息**: Environment variable DEEPSEEK_API_KEY is not set

### ollama
- **Type**: ollama
- **Model**: qwen2.5:14b
- **Endpoint**: http://localhost:11434/v1
- **API Key**: 未设置
- **配置检查**: PASS
- **连接检查**: FAIL
- **响应检查**: FAIL

## 修复建议

没有可用的 LLM Provider。请按以下步骤排查：

### OpenAI
1. 获取 API Key: https://platform.openai.com/api-keys
2. 设置环境变量: `set OPENAI_API_KEY=sk-...`
3. 重新运行: `python scripts/check_llm.py`

### DeepSeek
1. 获取 API Key: https://platform.deepseek.com/api_keys
2. 设置环境变量: `set DEEPSEEK_API_KEY=sk-...`
3. 重新运行: `python scripts/check_llm.py`

### Local (vLLM/Ollama)
1. 安装 vLLM 或 Ollama
2. 启动模型服务
3. 设置环境变量: `set LOCAL_LLM_ENDPOINT=http://localhost:8000/v1`
4. 重新运行: `python scripts/check_llm.py`

详细配置请参考: `docs/LLM_Configuration_Guide_CN.md`
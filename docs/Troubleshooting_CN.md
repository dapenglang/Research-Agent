# 故障排查指南

> Research Agent v8.2.2 — 常见问题与解决方案

---

## 目录

1. [环境与依赖问题](#1-环境与依赖问题)
2. [流水线阻塞问题](#2-流水线阻塞问题)
3. [Fallback 与运行模式问题](#3-fallback-与运行模式问题)
4. [注册表与缓存问题](#4-注册表与缓存问题)
5. [MCP 连接问题](#5-mcp-连接问题)
6. [LLM 与 API 问题](#6-llm-与-api-问题)
7. [状态与恢复问题](#7-状态与恢复问题)
8. [错误代码速查表](#8-错误代码速查表)

---

## 1. 环境与依赖问题

### 1.1 Python 版本不匹配

**症状：** `ModuleNotFoundError`、`ImportError` 或语法错误。

**原因：** 系统未使用 Python 3.12（本项目目标版本）。

**检查：**
```powershell
python --version
# 期望输出: Python 3.12.x
```

**解决：**
```powershell
# 激活 conda 环境
conda activate research_agent_v3

# 如果环境不存在，创建
conda create -n research_agent_v3 python=3.12 -y
conda activate research_agent_v3
pip install -r requirements.txt
```

**验证：**
```powershell
python --version  # 确认 3.12.x
python -c "import Research_Agent_v3; print('OK')"
```

---

### 1.2 缺少必需 Skill

**症状：** 日志输出 `Required skills missing: N skill(s) not installed`，或 `production` 模式下流水线被阻塞。

**原因：** `skill_registry.yaml` 中标记为 `required: true` 的 Skill 未安装。

**检查：**
```powershell
# 查看已安装的 Skill
python -c "
from Research_Agent_v3.infrastructure.skills.skill_runtime import SkillRuntime
rt = SkillRuntime()
report = rt.check_all_modules()
print(f'缺失必需 Skill 数: {report[\"total_required_missing\"]}')
for mid, mod in report['modules'].items():
    for m in mod['required_missing']:
        print(f'  Module {mid}: 缺失 {m[\"skill_name\"]}')
"
```

**解决：**
1. 确认 TRAE Skill 安装路径存在（默认 `c:/Users/<你的用户名>/.trae-cn/skills`）。
2. 通过 TRAE 客户端安装缺失的 Skill。
3. 手动触发重新扫描：
```powershell
python -c "
from Research_Agent_v3.infrastructure.skills.skill_runtime import SkillRuntime
rt = SkillRuntime()
result = rt.refresh()
print(f'已扫描到 {result[\"total_skills\"]} 个 Skill')
"
```
4. 如果仅用于开发/测试，将运行模式改为 `development` 或 `limited`（见第 3 节）。

---

### 1.3 Skill 扫描器在新机器上找不到 Skill

**症状：** `SkillRuntime` 报告 `total_skills: 0`，但 Skill 确实安装在 `~/.trae-cn/skills` 下。

**原因：** `SkillScanner` 默认扫描路径硬编码为 `c:/Users/langd/.trae-cn/skills`，在换机器后用户名不同导致路径不匹配。

**检查：**
```powershell
python -c "
from pathlib import Path
from Research_Agent_v3.infrastructure.skills.skill_scanner import SkillScanner
default_dir = SkillScanner.TRAE_SKILLS_DIR
print(f'默认扫描路径: {default_dir}')
print(f'路径存在: {default_dir.exists()}')

# 检查当前用户的实际路径
actual = Path.home() / '.trae-cn' / 'skills'
print(f'实际路径: {actual}')
print(f'实际路径存在: {actual.exists()}')
"
```

**解决：**
1. 删除旧的扫描缓存文件，强制重新扫描：
```powershell
del "D:\Research Agent\Research_Agent_v3\infrastructure\skills\installed_skills.json"
```
2. 手动指定扫描路径：
```python
from Research_Agent_v3.infrastructure.skills.skill_scanner import SkillScanner
from pathlib import Path

scanner = SkillScanner(skills_dir=Path.home() / ".trae-cn" / "skills")
result = scanner.scan()
print(f"扫描到 {result['total_skills']} 个 Skill")
```
3. 如果路径仍不匹配，修改 `skill_scanner.py` 中的 `TRAE_SKILLS_DIR`：
```python
TRAE_SKILLS_DIR = Path.home() / ".trae-cn" / "skills"
```

**验证：**
```powershell
python -c "
from Research_Agent_v3.infrastructure.skills.skill_runtime import SkillRuntime
rt = SkillRuntime()
print(f'已安装 Skill 数: {rt.get_total_count()}')
"
```

---

### 1.4 MCP 未配置

**症状：** 日志输出 `MCP servers not installed: [...]`，或 `production` 模式下流水线被阻塞。

**原因：** `mcp_registry.yaml` 中启用的 MCP 服务器未安装或环境变量未设置。

**检查：**
```powershell
python -c "
from Research_Agent_v3.infrastructure.mcp.mcp_manager import MCPManager
mgr = MCPManager()
report = mgr.check_all_availability()
print(f'已启用: {report[\"total_enabled\"]}')
print(f'已安装: {report[\"installed_count\"]}')
print(f'已配置: {report[\"configured_count\"]}')
for name, r in report['servers'].items():
    status = 'OK' if r['installed'] else 'MISSING'
    print(f'  {name}: {status} — {r[\"issues\"]}')
"
```

**解决：**
1. 安装缺失的 MCP 服务器（通过 `uvx` 或 `npx`）：
```powershell
# arxiv MCP
uvx arxiv-mcp-server --help

# paper-search MCP
uvx paper-search-mcp --help

# drawio MCP
npx -y @drawio/mcp --help
```
2. 设置所需环境变量（如 Zotero 需要 API Key）。
3. 在 `development` 模式下可继续运行（MCP 缺失触发 Fallback）。

---

## 2. 流水线阻塞问题

### 2.1 文献数量不足（< 50 篇）阻塞流水线

**症状：** 流水线在 Module 03 前返回 `blocked`，提示 `Literature gate FAILED: N papers found, need at least 50`。

**原因：** 文献质量门控要求 `data/literature/` 目录下至少有 50 篇论文（PDF 或 LaTeX），当前数量不足。

**检查：**
```powershell
python -c "
from pathlib import Path
root = Path('D:/Research Agent/Research_Agent_v3/data/literature')
pdf_dir = root / 'pdf'
latex_dir = root / 'latex'

pdf_count = sum(1 for f in pdf_dir.iterdir() if f.suffix.lower() == '.pdf' and f.stat().st_size > 1024) if pdf_dir.exists() else 0
latex_count = sum(1 for d in latex_dir.iterdir() if d.is_dir() and list(d.rglob('*.tex'))) if latex_dir.exists() else 0

print(f'PDF: {pdf_count} 篇')
print(f'LaTeX: {latex_count} 篇')
print(f'总计: {pdf_count + latex_count} 篇 (需要 >= 50)')
"
```

**解决：**

方案 A — 补充文献（推荐）：
1. 将论文 PDF 放入 `data/literature/pdf/`。
2. 或将 LaTeX 源码放入 `data/literature/latex/<paper_id>/`。
3. PDF 文件需 > 1KB 才被计入。

方案 B — 跳过门控（仅开发/测试）：
```powershell
# 使用 skip_gates 参数启动
python -m Research_Agent_v3.cli.cli start --task research_task.yaml --skip-gates
```

或在代码中设置：
```python
orchestrator = PipelineOrchestrator(
    task_config_path="configs/research_task.yaml",
    skip_gates=True
)
```

> 注意：跳过文献门控会导致 Module 03-05 缺乏足够数据支撑，输出质量下降。

---

### 2.2 模块执行失败

**症状：** 模块状态为 `FAIL`，流水线在非合成模式下中止。

**原因：** 模块在 `validate_input`、`execute` 或 `validate_output` 阶段失败。

**检查：**
```powershell
python -m Research_Agent_v3.cli.cli status --task research_task.yaml
```

查看 `module_states` 中对应模块的 `errors` 字段。

**解决：**
1. 检查模块的 `schema.py` 和 `manifest.yaml` 了解必需的输入/输出。
2. 确认上游模块产出了所有必需文件。
3. 使用 `rerun` 从失败模块重新执行：
```powershell
python -m Research_Agent_v3.cli.cli rerun --task research_task.yaml --from <module_id>
```
4. 在 `synthetic_research` 模式下，模块失败不会中止流水线（自动使用 stub 输出继续）。

---

## 3. Fallback 与运行模式问题

### 3.1 Production 模式下 Fallback 被阻止

**症状：** 模块收到 `get_fallback()` 返回的 `{"action": "block"}`，抛出异常或流水线中止。

**原因：** `production` 模式下 `allow_fallback: false`，所有 Fallback 策略均被阻止。

**检查：**
```powershell
python -c "
import yaml
cfg = yaml.safe_load(open('D:/Research Agent/Research_Agent_v3/configs/external_dependency.yaml'))
print(f'当前运行模式: {cfg[\"run_mode\"]}')

policy = yaml.safe_load(open('D:/Research Agent/Research_Agent_v3/configs/dependency_policy.yaml'))
mode = policy['mode_constraints']['production']
print(f'Production 允许 Fallback: {mode[\"allow_fallback\"]}')
"
```

**解决：**

方案 A — 安装缺失的依赖（推荐用于 production）：
1. 安装缺失的必需 Skill（见 1.2）。
2. 安装缺失的 MCP 服务器（见 1.4）。
3. 配置真实 LLM（见第 6 节）。

方案 B — 切换运行模式（降级使用）：
```yaml
# configs/external_dependency.yaml
run_mode: limited  # 将 production 改为 limited
```

| 模式 | 行为 |
|------|------|
| `production` | Fallback 被阻止，缺少必需依赖时阻塞流水线 |
| `limited` | Fallback 允许，缺少依赖时自动降级 |
| `development` | Fallback 允许，允许 Mock 输出 |

---

### 3.2 Fallback 策略不生效

**症状：** 依赖缺失但模块未按预期 Fallback，而是报错。

**原因：** `dependency_type` 参数与 `dependency_policy.yaml` 中的策略键不匹配。

**检查：**
```powershell
python -c "
import yaml
policy = yaml.safe_load(open('D:/Research Agent/Research_Agent_v3/configs/dependency_policy.yaml'))
print('Skill Fallback 策略:')
for k, v in policy.get('skill_fallback', {}).items():
    print(f'  {k}: action={v[\"action\"]}')
print('MCP Fallback 策略:')
for k, v in policy.get('mcp_fallback', {}).items():
    print(f'  {k}: action={v[\"action\"]}')
"
```

**解决：**
1. 确认模块调用的 `dependency_type` 与策略键完全匹配（如 `skill:light-literature-search`）。
2. 如果没有精确匹配，系统会使用 `skill:default` 或 `mcp:default` 兜底策略。
3. 如需自定义策略，在 `configs/dependency_policy.yaml` 中添加新条目。

---

## 4. 注册表与缓存问题

### 4.1 注册表损坏恢复

**症状：** `skill_registry.yaml` 或 `mcp_registry.yaml` 解析失败，`SkillRuntime` 或 `MCPManager` 初始化报错。

**原因：** YAML 文件被意外修改、格式损坏或包含非法字符。

**检查：**
```powershell
python -c "
import yaml

files = [
    'D:/Research Agent/Research_Agent_v3/infrastructure/skills/skill_registry.yaml',
    'D:/Research Agent/Research_Agent_v3/infrastructure/mcp/mcp_registry.yaml',
    'D:/Research Agent/Research_Agent_v3/configs/dependency_policy.yaml',
    'D:/Research Agent/Research_Agent_v3/configs/external_dependency.yaml',
]
for f in files:
    try:
        yaml.safe_load(open(f, encoding='utf-8'))
        print(f'{f}: OK')
    except Exception as e:
        print(f'{f}: 损坏 — {e}')
"
```

**解决：**

Skill 注册表恢复：
```powershell
# 1. 删除已安装 Skill 缓存，触发重新扫描
del "D:\Research Agent\Research_Agent_v3\infrastructure\skills\installed_skills.json"

# 2. 重新扫描
python -c "
from Research_Agent_v3.infrastructure.skills.skill_runtime import SkillRuntime
rt = SkillRuntime()
result = rt.refresh()
print(f'重新扫描到 {result[\"total_skills\"]} 个 Skill')
"
```

MCP 注册表恢复：
```powershell
# 1. 重置 MCP 状态字段（重新检测安装状态）
python -c "
from Research_Agent_v3.infrastructure.mcp.mcp_manager import MCPManager
mgr = MCPManager()
report = mgr.check_all_availability()
print(f'已检测: {report[\"installed_count\"]}/{report[\"total_enabled\"]} 已安装')
"
```

通用恢复：
1. 如果 YAML 文件本身损坏，从版本控制恢复：`git checkout -- <file>`
2. 如果没有备份，参考 `skill_registry.yaml` 的格式重新创建。
3. Orchestrator 初始化时对 YAML 解析失败是容错的（返回空字典 + 日志警告），不会崩溃。

---

### 4.2 SkillScanner 扫描结果为空

**症状：** `SkillRuntime.get_total_count()` 返回 0，但 Skill 确实存在。

**原因：** 扫描缓存过期、扫描路径不存在、或 Skill 缺少 `SKILL.md` 文件。

**检查：**
```powershell
python -c "
import json
from pathlib import Path

cache = Path('D:/Research Agent/Research_Agent_v3/infrastructure/skills/installed_skills.json')
if cache.exists():
    data = json.load(open(cache, encoding='utf-8'))
    print(f'缓存时间: {data.get(\"scan_time\")}')
    print(f'扫描路径: {data.get(\"skills_dir\")}')
    print(f'Skill 数: {data.get(\"total_skills\")}')
else:
    print('缓存文件不存在')

# 检查 Skill 目录
skills_dir = Path.home() / '.trae-cn' / 'skills'
if skills_dir.exists():
    dirs = [d.name for d in skills_dir.iterdir() if d.is_dir()]
    has_skill_md = [d for d in skills_dir.iterdir() if d.is_dir() and (d / 'SKILL.md').exists()]
    print(f'目录存在，子目录数: {len(dirs)}')
    print(f'有 SKILL.md 的目录数: {len(has_skill_md)}')
else:
    print(f'目录不存在: {skills_dir}')
"
```

**解决：**
1. 删除缓存并重新扫描（见 4.1）。
2. 确认每个 Skill 目录下都有 `SKILL.md` 文件（扫描器只识别包含此文件的目录）。
3. 确认扫描路径正确（见 1.3）。

---

## 5. MCP 连接问题

### 5.1 MCP 连接超时

**症状：** `_check_tested()` 返回 `False`，日志提示 `connection test failed`。

**原因：** MCP 服务器启动超时（默认 5 秒）、网络问题、或命令未安装。

**检查：**
```powershell
# 手动测试 MCP 命令是否可用
uvx arxiv-mcp-server --help
uvx paper-search-mcp --help
npx -y @drawio/mcp --help

# 检查命令是否存在
python -c "
import shutil
for cmd in ['uvx', 'npx', 'python']:
    print(f'{cmd}: {shutil.which(cmd)}')
"
```

**解决：**
1. 安装 `uv`（提供 `uvx` 命令）：
```powershell
pip install uv
```
2. 安装 Node.js（提供 `npx` 命令）：从 https://nodejs.org 下载安装。
3. 首次运行 `uvx` 或 `npx` 会下载依赖，可能较慢。预先手动运行一次以缓存。
4. 如果是网络问题，配置代理（见 `configs/machine.yaml`）。
5. `tested: False` 不阻塞流水线（在 `limited`/`development` 模式下），只有 `installed: False` 才会触发 Fallback。

---

### 5.2 MCP 环境变量未配置

**症状：** MCP 服务器 `configured: False`，状态显示 `CONFIGURED (missing env)`。

**原因：** `mcp_registry.yaml` 中配置了 `env` 字段但环境变量未设置。

**检查：**
```powershell
python -c "
from Research_Agent_v3.infrastructure.mcp.mcp_manager import MCPManager
mgr = MCPManager()
for name, cfg in mgr.list_enabled().items():
    env = cfg.get('env', {})
    if env:
        import os
        for k, v in env.items():
            val = v if not (isinstance(v, str) and v.startswith('$')) else os.environ.get(v[1:], '')
            print(f'{name}.{k}: {\"已设置\" if val else \"未设置\"}')
"
```

**解决：**
1. 设置所需的环境变量：
```powershell
$env:ZOTERO_API_KEY = "你的Zotero API Key"
$env:ZOTERO_LIBRARY_ID = "你的Library ID"
```
2. 或在 `mcp_registry.yaml` 中将对应服务器设为 `enabled: false`。

---

## 6. LLM 与 API 问题

### 6.1 LLM API Key 缺失

**症状：** LLM 门控警告 `No real LLM provider available`，或 LLM 调用返回认证错误。

**原因：** 环境变量未设置或配置文件中 API Key 为空。

**检查：**
```powershell
python -c "
import os
keys = ['OPENAI_API_KEY', 'DEEPSEEK_API_KEY', 'DASHSCOPE_API_KEY']
for k in keys:
    val = os.environ.get(k, '')
    print(f'{k}: {\"已设置 (长度: \" + str(len(val)) + \")\" if val else \"未设置\"}')
"
```

**解决：**
1. 设置 API Key 环境变量（详见 `docs/LLM_Configuration_Guide_CN.md`）：
```powershell
# DeepSeek（推荐，国内可用）
$env:DEEPSEEK_API_KEY = "sk-你的密钥"

# 或 OpenAI
$env:OPENAI_API_KEY = "sk-你的密钥"
```
2. 确认 `configs/llm.yaml` 中 `provider` 字段指向已配置 Key 的提供商。
3. 在 `production` 模式下，LLM 必需模块（05/06/10/12/14）缺少真实 LLM 会触发门控警告。

---

### 6.2 LLM 回退到模板模式

**症状：** 日志输出 `LLM unavailable, using template mode generation`，模块输出质量明显下降。

**原因：** LLM 不可用，触发了 `llm_fallback` 策略（`action: template`）。

**检查：**
```powershell
python -c "
from Research_Agent_v3.infrastructure.llm_runtime.runtime import LLMRuntime
runtime = LLMRuntime('D:/Research Agent/Research_Agent_v3/configs')
runtime.load()
status = runtime.get_status()
print(status)
"
```

**解决：**
1. 配置可用的 LLM 提供商（见 6.1）。
2. 确认 `configs/llm_routing.yaml` 中任务路由指向已配置的提供商。
3. 在 `production` 模式下，`require_real_llm: true`，模板模式不被允许。

---

## 7. 状态与恢复问题

### 7.1 状态文件损坏

**症状：** `resume` 命令失败，报 `StateError: Malformed state file`。

**原因：** `state/<task_id>/research_state.yaml` 文件损坏或格式错误。

**解决：**
```powershell
# 方案 A: 从头开始（删除状态文件）
del "D:\Research Agent\Research_Agent_v3\state\<task_id>\research_state.yaml"
python -m Research_Agent_v3.cli.cli start --task research_task.yaml

# 方案 B: 从指定模块重新执行
python -m Research_Agent_v3.cli.cli rerun --task research_task.yaml --from 01
```

---

### 7.2 模块导入错误

**症状：** `ModuleError: Module XX implementation not found` 或 `does not expose class XxxImplementation`。

**原因：** 模块目录结构不完整，或实现类名与 `IMPL_CLASS_MAP` 不匹配。

**检查：**
```powershell
python -c "
from pathlib import Path
root = Path('D:/Research Agent/Research_Agent_v3/modules')
for d in sorted(root.iterdir()):
    if d.is_dir() and not d.name.startswith('_'):
        impl = d / 'implementation.py'
        interface = d / 'interface.py'
        manifest = d / 'manifest.yaml'
        print(f'{d.name}: impl={impl.exists()} interface={interface.exists()} manifest={manifest.exists()}')
"
```

**解决：**
1. 确认每个模块目录包含 `implementation.py`、`interface.py`、`manifest.yaml`。
2. 确认实现类名与 `pipeline.py` 中 `IMPL_CLASS_MAP` 一致。
3. 清除 Python 缓存：`del /s /q "D:\Research Agent\Research_Agent_v3\__pycache__"`。

---

### 7.3 路径问题（Windows）

**症状：** `FileNotFoundError` 或路径相关错误。

**解决：**
1. YAML 配置文件中使用正斜杠 `/`（如 `D:/ResearchData/models`）。
2. 避免路径中包含空格（如使用 `Research_Agent_v3` 而非 `Research Agent v3`）。
3. 使用 `pathlib.Path` 处理路径，自动兼容 `\` 和 `/`。

---

## 8. 错误代码速查表

### 8.1 流水线状态码

| 状态 | 含义 | 处理建议 |
|------|------|---------|
| `blocked` | 前置检查失败，流水线被阻塞 | 查看返回的 `blocking_errors` 列表 |
| `failed` | 模块执行失败，流水线中止 | 查看对应模块的 `errors` 字段 |
| `completed` | 流水线成功完成 | 无需处理 |
| `error` | 操作不合法（如状态不允许 resume） | 查看返回的 `message` 字段 |

### 8.2 模块状态码

| 状态 | 含义 | 处理建议 |
|------|------|---------|
| `PASS` | 所有硬性要求通过 | 无需处理 |
| `WARNING` | 部分硬性要求未通过 | 检查 `quality_assessment` 详情 |
| `FAIL` | 模块执行或验证失败 | 查看 `errors` 字段，使用 `rerun` 重试 |
| `SKIPPED` | 模块被跳过 | 根据实验模式确认是否符合预期 |
| `NOT_STARTED` | 模块尚未执行 | 正常初始状态 |

### 8.3 异常类型

| 异常类 | 触发场景 | 解决方案 |
|--------|---------|---------|
| `ConfigError` | 配置文件缺失或格式错误 | 检查 `configs/` 目录 |
| `ValidationError` | 输入/输出验证失败 | 检查模块 `schema.py` 和上游输出 |
| `ModuleError` | 模块加载或执行错误 | 检查模块目录结构和类名 |
| `StateError` | 非法状态转换或状态文件损坏 | 删除状态文件重新开始 |
| `StorageError` | 存储读写失败 | 检查磁盘空间和权限 |
| `ModelError` | 本地模型加载失败 | 检查 `model_registry.yaml` 路径 |
| `LLMProviderError` | LLM 调用失败 | 检查 API Key 和网络 |
| `ExperimentError` | 实验执行中断 | 使用 `resume` 恢复 |
| `ProvenanceError` | 溯源完整性违规 | 检查 `data_origin` 标签 |
| `CheckpointError` | 检查点缺失或损坏 | 删除检查点，重新执行 |

### 8.4 门控错误

| 门控 | 触发条件 | 错误信息关键词 | 解决方案 |
|------|---------|--------------|---------|
| 文献质量门控 | 论文数 < 50 | `Literature gate FAILED` | 补充文献或 `--skip-gates` |
| LLM 门控 | LLM 必需模块无真实 LLM | `LLM gate WARNING` | 配置 API Key（仅警告不阻塞） |
| Skill 预检 | 必需 Skill 缺失（production） | `Required skills missing` | 安装 Skill 或切换模式 |
| MCP 预检 | MCP 未安装（production） | `MCP servers not installed` | 安装 MCP 或切换模式 |

### 8.5 Fallback action 返回值

| action | 含义 | 模块应做 |
|--------|------|---------|
| `block` | 禁止 Fallback（production 模式） | 抛出异常，中止执行 |
| `llm_prompt` | 使用 LLM 提示词替代 | 加载 `prompt_template` 指定的提示词 |
| `internal_implementation` | 使用内置实现 | 调用内置下载器/解析器 |
| `matplotlib` | 使用 matplotlib 绘图 | 调用 matplotlib 生成图表 |
| `local_file` | 使用本地文件 | 读取本地 .bib 等文件 |
| `template` | 使用模板模式 | 使用预定义模板生成内容 |
| `skip` | 跳过该功能 | 记录日志，继续执行 |
| `none` | 无匹配策略 | 模块自行决定处理方式 |

---

## 快速诊断命令汇总

```powershell
# 1. 检查 Python 环境
python --version
conda info --envs

# 2. 检查配置文件完整性
python -c "
import yaml
from pathlib import Path
root = Path('D:/Research Agent/Research_Agent_v3/configs')
for f in root.glob('*.yaml'):
    try:
        yaml.safe_load(open(f, encoding='utf-8'))
        print(f'{f.name}: OK')
    except Exception as e:
        print(f'{f.name}: ERROR — {e}')
"

# 3. 检查 Skill 状态
python -c "
from Research_Agent_v3.infrastructure.skills.skill_runtime import SkillRuntime
rt = SkillRuntime()
print(f'Skill 总数: {rt.get_total_count()}')
report = rt.check_all_modules()
print(f'缺失必需 Skill: {report[\"total_required_missing\"]}')
"

# 4. 检查 MCP 状态
python -c "
from Research_Agent_v3.infrastructure.mcp.mcp_manager import MCPManager
mgr = MCPManager()
report = mgr.check_all_availability()
print(f'已安装: {report[\"installed_count\"]}/{report[\"total_enabled\"]}')
"

# 5. 检查 LLM 状态
python -c "
from Research_Agent_v3.infrastructure.llm_runtime.runtime import LLMRuntime
rt = LLMRuntime('D:/Research Agent/Research_Agent_v3/configs')
rt.load()
print(rt.get_status())
"

# 6. 检查文献数量
python -c "
from pathlib import Path
root = Path('D:/Research Agent/Research_Agent_v3/data/literature')
pdf = sum(1 for f in (root/'pdf').iterdir() if f.suffix=='.pdf' and f.stat().st_size>1024) if (root/'pdf').exists() else 0
latex = sum(1 for d in (root/'latex').iterdir() if d.is_dir() and list(d.rglob('*.tex'))) if (root/'latex').exists() else 0
print(f'文献: {pdf+latex} 篇 (需要 >= 50)')
"

# 7. 检查运行模式
python -c "
import yaml
cfg = yaml.safe_load(open('D:/Research Agent/Research_Agent_v3/configs/external_dependency.yaml'))
print(f'运行模式: {cfg[\"run_mode\"]}')
"

# 8. 检查流水线状态
python -m Research_Agent_v3.cli.cli status --task research_task.yaml
```

---

## 相关文件

| 文件 | 说明 |
|------|------|
| `orchestrator/pipeline.py` | 流水线编排器，门控与错误处理 |
| `core/exceptions/exceptions.py` | 全部异常类型定义 |
| `core/state/state_machine.py` | 状态机与状态文件管理 |
| `configs/external_dependency.yaml` | 运行模式配置 |
| `configs/dependency_policy.yaml` | Fallback 策略定义 |
| `configs/llm.yaml` | LLM 配置 |
| `infrastructure/skills/skill_scanner.py` | Skill 扫描器 |
| `infrastructure/skills/skill_registry.yaml` | Skill 注册表 |
| `infrastructure/mcp/mcp_manager.py` | MCP 管理器 |
| `infrastructure/mcp/mcp_registry.yaml` | MCP 注册表 |
| `scripts/check_portability.py` | 环境可移植性检查脚本 |
| `docs/LLM_Configuration_Guide_CN.md` | LLM 配置详细指南 |

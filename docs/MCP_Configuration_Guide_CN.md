# Research Agent v8.2.2 — MCP 配置指南

> 本文档说明 MCP（Model Context Protocol）服务器注册表的结构、三态状态机、安装方法、连通性测试及降级策略管理。

---

## 目录

1. [注册表位置](#1-注册表位置)
2. [三态状态机](#2-三态状态机)
3. [注册表字段说明](#3-注册表字段说明)
4. [安装 MCP 服务器](#4-安装-mcp-服务器)
5. [测试 MCP 连通性](#5-测试-mcp-连通性)
6. [运行 check_mcp.py](#6-运行-check_mcppy)
7. [降级策略管理](#7-降级策略管理)
8. [注册表示例](#8-注册表示例)

---

## 1. 注册表位置

MCP 注册表位于项目基础设施层，**不会被迁移或移动**：

```
infrastructure/mcp/mcp_registry.yaml
```

相关文件：

| 文件 | 路径 | 用途 |
|------|------|------|
| 注册表 | `infrastructure/mcp/mcp_registry.yaml` | MCP 服务器定义与状态 |
| 管理器 | `infrastructure/mcp/mcp_manager.py` | MCP 调用与生命周期管理 |

> **重要**：`mcp_registry.yaml` 是项目内部文件，定义"需要哪些 MCP 服务器"及当前安装状态。`check_mcp.py` 运行时会自动更新其中的状态字段。

---

## 2. 三态状态机

每个 MCP 服务器有三个独立的状态字段，构成三态状态机：

```
installed → configured → tested
```

| 状态 | 检测方法 | 含义 |
|------|----------|------|
| `installed` | 检查 `command` 对应的可执行文件是否在 PATH 中可用 | MCP 服务器程序已安装 |
| `configured` | 检查 `env` 中所有环境变量是否已设置（非空或已在系统环境变量中存在） | 必需的环境变量已配置 |
| `tested` | 执行 `command --help <args[0]>` 检查返回码是否为 0 或 2 | MCP 服务器可正常启动 |

### 状态组合含义

| installed | configured | tested | 含义 |
|-----------|------------|--------|------|
| false | false | false | 完全未安装 |
| true | false | false | 程序已装但缺少配置（如 API Key） |
| true | true | false | 已配置但运行时测试失败 |
| true | true | true | 完全就绪 |

### 特殊情况

- 如果服务器没有 `env` 字段（或为空），`configured` 自动判定为 `true`
- `tested` 检查超时时间为 5 秒

---

## 3. 注册表字段说明

注册表顶层包含两个键：

```yaml
mcp_servers:    # MCP 服务器定义
  <server_name>:
    ...
categories:     # 分类说明
  literature: 文献检索与下载
  ...
```

每个 MCP 服务器包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | string | 通信类型，当前统一为 `stdio` |
| `command` | string | 启动命令（如 `uvx`、`npx`） |
| `args` | list | 命令参数列表 |
| `description` | string | MCP 服务器功能描述 |
| `category` | string | 分类（见下表） |
| `enabled` | bool | 是否启用该服务器 |
| `installed` | bool | 程序是否已安装（由 check_mcp.py 自动更新） |
| `configured` | bool | 环境变量是否已配置（由 check_mcp.py 自动更新） |
| `tested` | bool | 连通性测试是否通过（由 check_mcp.py 自动更新） |
| `config_path` | string | 额外配置文件路径（可空） |
| `install_method` | string | 安装方式（`uvx` / `npx`） |
| `env` | dict | 需要的环境变量（可空） |
| `fallback` | string | 降级策略引用名，对应 `dependency_policy.yaml` |

### 分类（category）

| 分类 | 说明 |
|------|------|
| `literature` | 文献检索与下载 |
| `reference` | 引用与文献管理 |
| `knowledge_base` | 知识库集成 |
| `figure` | 科研绘图与可视化 |
| `web` | 网络搜索与内容提取 |

---

## 4. 安装 MCP 服务器

### 4.1 前置条件

安装 MCP 服务器需要以下工具之一：

| 工具 | 对应 install_method | 安装方式 |
|------|---------------------|----------|
| `uvx` | uvx | `pip install uv` 或 `pipx install uv` |
| `npx` | npx | 安装 Node.js（自带 npx） |

验证工具是否可用：

```bash
uvx --version
npx --version
```

### 4.2 安装 uvx 类型服务器

`uvx` 是 Python 包运行器，用于安装 Python 编写的 MCP 服务器。

**arxiv MCP 服务器**：
```bash
# uvx 会在首次运行时自动安装，无需单独安装
# 验证可用性：
uvx arxiv-mcp-server --help
```

**fetch MCP 服务器**：
```bash
uvx mcp-server-fetch --help
```

**paper-search MCP 服务器**：
```bash
uvx paper-search-mcp --help
```

### 4.3 安装 npx 类型服务器

`npx` 是 Node.js 包运行器，用于安装 JavaScript/TypeScript 编写的 MCP 服务器。

**drawio MCP 服务器**：
```bash
npx -y @drawio/mcp --help
```

**chart MCP 服务器**：
```bash
npx -y @antv/mcp-server-chart --help
```

**obsidian MCP 服务器**：
```bash
npx -y obsidian-mcp --help
```

### 4.4 配置环境变量

部分 MCP 服务器需要环境变量。以 Zotero 为例：

1. 编辑 `infrastructure/mcp/mcp_registry.yaml` 中的 `env` 字段：
   ```yaml
   zotero:
     env:
       ZOTERO_API_KEY: "你的Zotero API Key"
       ZOTERO_LIBRARY_ID: "你的Library ID"
   ```
2. 或在系统环境变量中设置：
   ```bash
   set ZOTERO_API_KEY=你的Key
   set ZOTERO_LIBRARY_ID=你的ID
   ```

### 4.5 启用/禁用服务器

在注册表中修改 `enabled` 字段：

```yaml
zotero:
  enabled: false   # 改为 true 启用
```

`check_mcp.py` 只检查 `enabled: true` 的服务器。

---

## 5. 测试 MCP 连通性

### 5.1 自动测试

`check_mcp.py` 对每个已启用的服务器执行以下测试：

1. **installed 检查**：`shutil.which(command)` 判断命令是否在 PATH 中
2. **configured 检查**：遍历 `env` 字典，检查每个变量是否有值
3. **tested 检查**：运行 `[command, "--help", args[0]]`，超时 5 秒，返回码 0 或 2 视为通过

### 5.2 手动测试

单独测试某个 MCP 服务器：

```bash
# 测试 arxiv MCP
uvx arxiv-mcp-server --help

# 测试 fetch MCP
uvx mcp-server-fetch --help

# 测试 drawio MCP
npx -y @drawio/mcp --help
```

如果命令在 5 秒内返回帮助信息且返回码为 0 或 2，则测试通过。

---

## 6. 运行 check_mcp.py

### 6.1 命令

```bash
python scripts/check_mcp.py
```

### 6.2 脚本行为

该脚本会：

1. 读取 `infrastructure/mcp/mcp_registry.yaml`
2. 遍历所有 `enabled: true` 的服务器
3. 逐一检测 installed / configured / tested 状态
4. **自动更新注册表**中的状态字段
5. 有缺失时生成 `MCP_Install_Request.md`

### 6.3 输出示例

```
============================================================
MCP Check Report
============================================================
Total enabled MCPs: 5
Installed: 4
Configured: 4
Tested: 3
Status: FAIL

Details:
  arxiv              installed=Y configured=Y tested=Y
  paper-search       installed=Y configured=Y tested=Y
  zotero             installed=N configured=N tested=N
  drawio             installed=Y configured=Y tested=N
  chart              installed=Y configured=Y tested=N
  fetch              installed=Y configured=Y tested=Y

Install request generated: MCP_Install_Request.md
```

### 6.4 安装请求报告

`MCP_Install_Request.md` 包含：
- 缺失的 MCP 服务器列表
- 每个服务器的命令、安装方式、降级策略
- 安装命令
- 安装步骤说明

---

## 7. 降级策略管理

> **核心原则**：与 Skill 一样，MCP 的降级行为由 `dependency_policy.yaml` 统一管理，模块不得自行决定。

### 7.1 策略文件位置

```
configs/dependency_policy.yaml
```

### 7.2 MCP 降级策略

`mcp_registry.yaml` 中每个服务器的 `fallback` 字段引用 `dependency_policy.yaml` 中的策略键：

```yaml
# mcp_registry.yaml 中的条目
arxiv:
  fallback: "mcp:arxiv"   # 引用策略键

# dependency_policy.yaml 中对应的策略
mcp_fallback:
  "mcp:arxiv":
    action: "internal_implementation"
    message: "arxiv MCP unavailable, using built-in PaperDownloader"
```

### 7.3 降级行为类型

| action | 说明 | 适用场景 |
|--------|------|----------|
| `internal_implementation` | 使用内置实现替代 MCP | arxiv 搜索、paper-search 等 |
| `local_file` | 使用本地文件管理替代 | Zotero 等文献管理 |
| `llm_prompt` | 使用 LLM 提示词替代 | drawio 等图表生成 |
| `matplotlib` | 使用 matplotlib 内置绘图 | chart 等图表生成 |
| `skip` | 跳过该功能 | fetch 等非必需功能 |

### 7.4 当前 MCP 降级策略一览

| MCP 服务器 | fallback 键 | action | 说明 |
|------------|-------------|--------|------|
| arxiv | `mcp:arxiv` | internal_implementation | 使用内置 PaperDownloader |
| paper-search | `mcp:paper-search` | internal_implementation | 使用内置多源搜索 |
| zotero | `mcp:zotero` | local_file | 使用本地 .bib 文件 |
| drawio | `mcp:drawio` | llm_prompt | 输出绘图提示词供手动生成 |
| chart | `mcp:chart` | matplotlib | 使用 matplotlib 内置绘图 |
| fetch | `mcp:fetch` | skip | 跳过网页内容提取 |
| (默认) | `mcp:default` | skip | 跳过 |

### 7.5 运行模式约束

降级策略受运行模式约束（与 Skill 共享）：

| 模式 | 允许降级 | 允许 Mock |
|------|----------|-----------|
| `production` | 否 | 否 |
| `limited` | 是 | 否 |
| `development` | 是 | 是 |

在 production 模式下，MCP 不可用时不会自动降级，而是报错终止。

---

## 8. 注册表示例

以下是 `mcp_registry.yaml` 中 `arxiv` 服务器的完整条目：

```yaml
mcp_servers:
  arxiv:
    type: stdio
    command: uvx
    args:
    - arxiv-mcp-server
    description: arXiv 论文搜索、下载、LaTeX源码读取、引用图谱
    category: literature
    enabled: true
    installed: true
    configured: true
    tested: true
    config_path: ''
    install_method: uvx
    fallback: mcp:arxiv
```

对应的 `dependency_policy.yaml` 降级策略：

```yaml
mcp_fallback:
  "mcp:arxiv":
    action: "internal_implementation"
    message: "arxiv MCP unavailable, using built-in PaperDownloader"
```

当 arxiv MCP 的 `installed` 为 `false` 或 `tested` 为 `false` 时，模块通过 `pipeline.get_fallback()` 查询到 `mcp:arxiv` 策略，使用内置 `PaperDownloader` 替代。

---

## 常见问题

**Q: installed、configured、tested 三个状态有什么区别？**

`installed` 检查程序是否在 PATH 中；`configured` 检查环境变量是否设置；`tested` 检查程序是否能正常启动。三者独立，可以 installed=true 但 tested=false（程序已装但运行异常）。

**Q: 为什么 tested 一直显示 false？**

`tested` 通过运行 `command --help args[0]` 检测。如果该命令不支持 `--help` 参数、启动超时（>5秒）、或返回码不是 0/2，都会判定为 false。这不一定影响实际使用，但建议排查原因。

**Q: 如何添加一个新的 MCP 服务器？**

在 `infrastructure/mcp/mcp_registry.yaml` 的 `mcp_servers` 下添加新条目，填写所有字段。`fallback` 必须引用 `dependency_policy.yaml` 中已定义的策略键。添加后运行 `python scripts/check_mcp.py` 验证。

**Q: check_mcp.py 会修改注册表吗？**

会。脚本运行时会自动更新每个已启用服务器的 `installed`、`configured`、`tested` 三个字段，将检测结果写回 `mcp_registry.yaml`。

**Q: 模块能自己决定 MCP 降级吗？**

不能。与 Skill 一样，模块必须通过 `pipeline.get_fallback()` 查询 `dependency_policy.yaml` 中的策略。这确保降级行为集中管理、可审计。

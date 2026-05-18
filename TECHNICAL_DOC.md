# Hermes Agent Job Hunt -- 项目技术文档

> 版本: 0.13.0 | 更新日期: 2026-05-15 | 作者: Hu Yaohua

---

## 目录

1. [项目概览](#1-项目概览)
2. [系统架构总览](#2-系统架构总览)
3. [核心模块详解](#3-核心模块详解)
   - 3.1 [Agent 核心引擎 (run_agent.py)](#31-agent-核心引擎-run_agentpy)
   - 3.2 [CLI 命令行界面 (hermes_cli/)](#32-cli-命令行界面-hermes_cli)
   - 3.3 [Gateway 多平台消息网关 (gateway/)](#33-gateway-多平台消息网关-gateway)
   - 3.4 [工具系统 (tools/)](#34-工具系统-tools)
   - 3.5 [插件系统 (plugins/)](#35-插件系统-plugins)
   - 3.6 [技能系统 (skills/)](#36-技能系统-skills)
   - 3.7 [Job Hunt 求职流水线 (job-hunt/)](#37-job-hunt-求职流水线-job-hunt)
   - 3.8 [Job Hunt 插件 (plugins/job-hunt/)](#38-job-hunt-插件-pluginsjob-hunt)
   - 3.9 [Trajectory 训练数据管线](#39-trajectory-训练数据管线)
4. [数据流架构](#4-数据流架构)
5. [配置体系](#5-配置体系)
6. [安全模型](#6-安全模型)
7. [测试体系](#7-测试体系)
8. [部署架构](#8-部署架构)

---

## 1. 项目概览

**Hermes Agent Job Hunt** 是基于 Nous Research 的 Hermes Agent 框架构建的自动化求职工具。系统通过 Telegram Bot 为用户（Hu Yaohua，九州大学院生，CV/ML/Edge AI 方向）提供从职位发现、匹配评分、简历生成到申请材料管理的全流程自动化服务。

### 1.1 核心特性

| 特性 | 描述 |
|------|------|
| 多平台消息 | 支持 20+ 平台（Telegram, Discord, Slack, WhatsApp, Signal, LINE, 钉钉, 飞书, 企业微信等） |
| 200+ 模型支持 | 通过 OpenRouter, Anthropic, Nous Portal, Gemini, Ollama 等接入 |
| 自动化求职流水线 | 职位发现 -> 去重 -> 评分 -> 简历生成 -> 申请材料打包 |
| 插件化架构 | 工具、钩子、平台适配器均可通过插件扩展 |
| 子代理委托 | 支持将任务委托给并行子代理执行 |
| 7 种终端后端 | Local, Docker, SSH, Singularity, Modal, Daytona, Vercel |
| 训练数据管线 | Trajectory 采集、压缩、ShareGPT 格式导出 |

### 1.2 技术栈

- **语言**: Python 3.11+
- **构建**: setuptools
- **核心依赖**: openai, httpx, rich, pyyaml, pydantic, prompt_toolkit, croniter
- **消息框架**: python-telegram-bot, discord.py, slack-bolt, mautrix
- **数据库**: SQLite + FTS5（会话存储）
- **测试**: pytest + pytest-xdist（并行执行）

---

## 2. 系统架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户交互层                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ Telegram │  │ Discord  │  │  Slack   │  │ CLI (prompt_tool)│ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘ │
│       │              │              │                 │           │
│  ┌────▼──────────────▼──────────────▼─────────────────▼────────┐ │
│  │              Gateway 消息网关 (gateway/run.py)               │ │
│  │  ┌─────────────┐ ┌──────────────┐ ┌──────────────────────┐ │ │
│  │  │ PlatformReg │ │ SessionStore │ │ DeliveryRouter       │ │ │
│  │  │ 平台注册表   │ │ 会话持久化    │ │ 投递路由              │ │ │
│  │  └─────────────┘ └──────────────┘ └──────────────────────┘ │ │
│  └────────────────────────┬────────────────────────────────────┘ │
│                           │                                      │
│  ┌────────────────────────▼────────────────────────────────────┐ │
│  │              AIAgent 核心引擎 (run_agent.py)                 │ │
│  │  ┌──────────┐ ┌───────────┐ ┌────────────┐ ┌────────────┐ │ │
│  │  │ LLM 调用 │ │ 工具分发   │ │ 上下文压缩  │ │ 模型切换    │ │ │
│  │  └──────────┘ └───────────┘ └────────────┘ └────────────┘ │ │
│  └────────────────────────┬────────────────────────────────────┘ │
│                           │                                      │
│  ┌────────────────────────▼────────────────────────────────────┐ │
│  │                    工具层 (tools/)                            │ │
│  │  terminal | file | browser | mcp | delegate | send_message  │ │
│  │  image_gen | video_gen | tts | vision | memory | web        │ │
│  └────────────────────────┬────────────────────────────────────┘ │
│                           │                                      │
│  ┌────────────────────────▼────────────────────────────────────┐ │
│  │              插件层 (plugins/) + 技能层 (skills/)             │ │
│  │  job-hunt | spotify | disk-cleanup | google_meet | kanban   │ │
│  │  79 SKILL.md 文件覆盖 25 个类别                               │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 2.1 核心数据流

1. **消息入口**: 用户通过 Telegram/Discord/CLI 发送消息
2. **网关路由**: `GatewayRunner._handle_message()` 进行认证、命令分发、会话管理
3. **Agent 循环**: `AIAgent.run_conversation()` 执行 LLM 调用 -> 工具分发 -> 结果反馈的循环
4. **工具执行**: 81 个注册工具通过 `ToolRegistry` 分发执行
5. **插件钩子**: 17 个生命周期钩子点允许插件介入处理流程
6. **响应输出**: 通过平台适配器回传用户

---

## 3. 核心模块详解

### 3.1 Agent 核心引擎 (run_agent.py)

**文件**: `run_agent.py` (16,081 行, 801 KB)
**类**: `AIAgent` (line 1098)

这是整个系统的大脑，管理完整的 LLM 对话循环。

#### 3.1.1 初始化参数（60+ 参数）

| 参数类别 | 关键参数 | 说明 |
|---------|---------|------|
| 模型配置 | `base_url`, `api_key`, `provider`, `model`, `api_mode` | LLM 连接配置 |
| 迭代控制 | `max_iterations`, `iteration_budget`, `tool_delay` | 循环次数和预算 |
| 工具过滤 | `enabled_toolsets`, `disabled_toolsets` | 工具集开关 |
| 回调函数 | `tool_progress_callback`, `clarify_callback`, `stream_delta_callback` | 事件回调 |
| 平台身份 | `platform`, `user_id`, `chat_id`, `thread_id` | 消息来源标识 |
| 会话管理 | `session_id`, `checkpoints_enabled`, `session_db` | 状态持久化 |

#### 3.1.2 核心方法

| 方法 | 位置 | 功能 |
|------|------|------|
| `run_conversation()` | line 10729 | 主循环入口：构建消息 -> 调用 LLM -> 执行工具 -> 重复 |
| `chat()` | line 14606 | 简化的单消息接口 |
| `_execute_tool_calls()` | line 9510 | 分发助手消息中的工具调用 |
| `_execute_tool_calls_concurrent()` | line 9664 | 并行工具执行（含路径冲突检测） |
| `_interruptible_streaming_api_call()` | line 6707 | 可中断的流式 LLM API 调用 |
| `_compress_context()` | line 9291 | 上下文过长时自动压缩 |
| `switch_model()` | line 1518 | 对话中途热切换模型 |
| `_try_activate_fallback()` | line 7600 | 错误时自动切换备用模型 |
| `_save_trajectory()` | line 3843 | 保存对话轨迹到 JSONL |

#### 3.1.3 对话循环流程

```
用户消息
    │
    ▼
build messages (system prompt + history + user input)
    │
    ▼
LLM API call (streaming, interruptible)
    │
    ├── 文本响应 → 返回用户
    │
    └── 工具调用 → _execute_tool_calls()
                        │
                        ├── 并行执行 (无冲突时)
                        └── 顺序执行 (有路径冲突时)
                            │
                            ▼
                    工具结果追加到消息
                            │
                            ▼
                    检查迭代预算
                            │
                            ├── 未超限 → 回到 LLM 调用
                            └── 超限 → 压缩上下文或终止
```

---

### 3.2 CLI 命令行界面 (hermes_cli/)

**入口**: `hermes_cli/main.py` (12,176 行)
**版本**: 0.13.0

#### 3.2.1 模块分层

| 层级 | 文件 | 职责 |
|------|------|------|
| 入口 | `main.py`, `_parser.py` | argparse 构建、子命令分发 |
| 命令注册 | `commands.py` | 命令定义的单一事实来源 |
| 网关管理 | `gateway.py`, `gateway_windows.py` | 网关生命周期管理 |
| 配置 | `config.py`, `auth.py`, `auth_commands.py` | 配置加载、认证管理 |
| 插件 | `plugins.py`, `plugins_cmd.py` | 插件发现、加载、生命周期 |
| 交互 | `callbacks.py`, `curses_ui.py`, `banner.py` | TUI 交互组件 |
| 辅助 | 60+ 文件 | 模型切换、配置向导、健康检查等 |

#### 3.2.2 命令注册系统

**文件**: `hermes_cli/commands.py` (71.7K)

`COMMAND_REGISTRY` 是所有斜杠命令的**单一事实来源**，被以下组件引用：

- CLI 帮助文本生成
- Gateway 命令分发
- Telegram BotCommands 菜单
- Slack 子命令映射
- Discord 技能命令
- 自动补全引擎

核心数据结构：

```python
@dataclass(frozen=True)
class CommandDef:
    name: str                    # 命令名 (如 "reset")
    description: str             # 描述
    category: str                # 分类 (Session, Config, Tools, Info, Exit)
    aliases: tuple[str, ...]     # 别名
    args_hint: str               # 参数提示
    subcommands: tuple[str, ...] # 子命令列表
    cli_only: bool               # 仅 CLI 可用
    gateway_only: bool           # 仅 Gateway 可用
    gateway_config_gate: str     # 需要的 Gateway 配置项
```

#### 3.2.3 Gateway 调用链

```
hermes gateway run
    │
    ▼
main.py: cmd_gateway(args)
    │
    ▼
gateway.py: gateway_command(args)
    │
    ▼
gateway.py: _gateway_command_inner(args)
    │
    ├── "run"    → run_gateway() → gateway.run.start_gateway()
    ├── "setup"  → gateway_setup() (交互式平台配置)
    ├── "install"→ systemd/launchd/Windows 服务安装
    ├── "start"  → 平台特定的服务启动
    ├── "stop"   → 平台特定的服务停止
    ├── "restart"→ SIGUSR1 优雅重启
    └── "status" → PID 文件 + 运行时状态检查
```

#### 3.2.4 关键辅助模块

| 模块 | 用途 |
|------|------|
| `profiles.py` | 多 Profile 管理（`hermes profile`） |
| `model_switch.py` | 模型/Provider 切换 UI |
| `models.py` | 模型目录和 Provider 定义 (140K) |
| `tools_config.py` | 按平台的工具开关配置 (126K) |
| `skills_hub.py` | 技能搜索、安装、管理 |
| `kanban.py` | 多 Profile 协作看板 |
| `doctor.py` | 配置和依赖健康检查 |
| `web_server.py` | Web UI 仪表盘 (168K) |
| `cron.py` | 定时任务管理 |

---

### 3.3 Gateway 多平台消息网关 (gateway/)

**核心文件**: `gateway/run.py` (16,500+ 行, 776 KB)

#### 3.3.1 架构模式

Gateway 采用**中心辐射（Hub-and-Spoke）架构**：

- **Hub**: `GatewayRunner` -- 中央控制器
- **Spoke**: 各平台适配器 (`BasePlatformAdapter` 子类)

#### 3.3.2 核心类

**`GatewayRunner`** (line 1174):

| 属性 | 类型 | 说明 |
|------|------|------|
| `adapters` | `Dict[Platform, BasePlatformAdapter]` | 活跃的平台适配器 |
| `session_store` | `SessionStore` | 会话持久化 |
| `delivery_router` | `DeliveryRouter` | 定时任务/通知路由 |
| `pairing_store` | `PairingStore` | DM 配对码授权 |
| `_running_agents` | `Dict[str, Any]` | 每会话活跃 Agent |
| `_agent_cache` | `OrderedDict` | LRU Agent 缓存（128 容量，1h TTL） |
| `_session_model_overrides` | `dict` | 每会话模型覆盖 |

#### 3.3.3 消息处理管线

`GatewayRunner._handle_message()` (line 5683) 处理流程：

```
收到消息
    │
    ▼
1. 插件钩子: pre_gateway_dispatch (可跳过/重写/放行)
    │
    ▼
2. 用户认证: 白名单检查 / 配对码流程
    │
    ▼
3. 特殊拦截: /update 响应、clarify 响应、approve/deny 响应
    │
    ▼
4. 运行中 Agent 检查:
    │  ├── /status → 立即响应
    │  ├── /stop   → 强制终止 Agent
    │  ├── /new    → 中断 + 重置会话
    │  ├── /queue  → 排队（不中断）
    │  └── /steer  → 注入中途提示
    │
    ▼
5. 冷路径命令分发: resolve_command() → SlashAccessPolicy → 处理器
    │
    ▼
6. Agent 执行: _handle_message_with_agent()
```

#### 3.3.4 平台适配器

每个适配器继承 `BasePlatformAdapter` (line 1265)，实现三个抽象方法：

| 方法 | 说明 |
|------|------|
| `connect() -> bool` | 启动平台特定的事件循环 |
| `disconnect()` | 断开连接 |
| `send(chat_id, content, reply_to, metadata) -> SendResult` | 发送消息 |

**支持的 20+ 内建平台**：

| 平台 | 适配器文件 | 协议 |
|------|-----------|------|
| Telegram | `telegram.py` | python-telegram-bot |
| Discord | `discord.py` | discord.py |
| WhatsApp | `whatsapp.py` | Node.js bridge |
| Slack | `slack.py` | slack-bolt |
| Signal | `signal.py` | signal-cli HTTP |
| Mattermost | `mattermost.py` | REST API |
| Matrix | `matrix.py` | mautrix |
| Email | `email.py` | IMAP/SMTP |
| SMS | `sms.py` | Twilio |
| 钉钉 | `dingtalk.py` | DingTalk API |
| 飞书 | `feishu.py` | Feishu/Lark API |
| 企业微信 | `wecom.py` | WeCom API |
| 微信 | `weixin.py` | Weixin API |
| iMessage | `bluebubbles.py` | BlueBubbles |
| QQ | `qqbot/` | QQ Bot API |
| 元宝 | `yuanbao.py` | Tencent Yuanbao |
| Home Assistant | `homeassistant.py` | HA API |
| API Server | `api_server.py` | HTTP REST |
| Webhook | `webhook.py` | Generic webhook |

#### 3.3.5 会话管理

**文件**: `gateway/session.py`

- **SessionSource**: 消息来源描述（平台、聊天 ID、用户 ID、线程 ID 等）
- **SessionKey**: 确定性键生成 `agent:main:{platform}:{chat_type}:{chat_id}:{thread_id}:{user_id}`
- **SessionStore**: SQLite 持久化 + JSONL 后备
- **SessionResetPolicy**: "daily" / "idle" / "both" / "none"

**并发安全**: `gateway/session_context.py` 使用 `contextvars.ContextVar` 替代全局 `os.environ`，确保并发 asyncio 任务的会话隔离。

#### 3.3.6 辅助模块

| 模块 | 用途 |
|------|------|
| `platform_registry.py` | 平台注册表（支持插件注册） |
| `delivery.py` | 消息投递路由（本地文件/平台适配器） |
| `hooks.py` | 事件钩子系统（`~/.hermes/hooks/`） |
| `stream_consumer.py` | 流式响应桥接（同步 Agent -> 异步平台） |
| `channel_directory.py` | 频道/联系人目录（5 分钟刷新） |
| `pairing.py` | DM 配对码授权（8 位码，1 小时过期） |
| `slash_access.py` | 斜杠命令访问控制 |
| `display_config.py` | 每平台显示配置 |
| `status.py` | PID 文件 + 运行时状态 |
| `shutdown_forensics.py` | SIGTERM/SIGINT 诊断捕获 |

---

### 3.4 工具系统 (tools/)

**注册中心**: `tools/registry.py` -> `ToolRegistry` 单例
**编排层**: `model_tools.py` (36.8K)

#### 3.4.1 注册机制

每个工具文件在模块级别调用：

```python
registry.register(
    name="tool_name",
    toolset="category",
    schema={...},           # OpenAI function calling schema
    handler=handle_fn,      # 处理函数
    check_fn=available_fn,  # 可用性检查
    emoji="🔧",
    max_result_size=100000,
)
```

#### 3.4.2 工具分类（81 个工具）

| 类别 | 工具数 | 代表工具 |
|------|--------|---------|
| **终端/代码** | 2 | `terminal_tool` (98K), `code_execution_tool` (70K) |
| **文件操作** | 3 | `file_tools`, `file_operations`, `file_state` |
| **浏览器** | 5 | `browser_tool` (149K), `browser_cdp_tool`, `browser_camofox` |
| **MCP** | 3 | `mcp_tool` (137K), `mcp_oauth`, `mcp_oauth_manager` |
| **技能** | 5 | `skills_tool`, `skills_hub` (117K), `skills_guard` |
| **消息** | 2 | `send_message_tool` (81K), `discord_tool` |
| **委托** | 1 | `delegate_tool` (115K) |
| **媒体** | 5 | `image_generation_tool`, `video_generation_tool`, `tts_tool` |
| **记忆/状态** | 3 | `memory_tool`, `checkpoint_manager`, `session_search_tool` |
| **Web** | 3 | `web_tools` (64K), `url_safety`, `website_policy` |
| **集成** | 7 | `homeassistant_tool`, `feishu_doc_tool`, `kanban_tools` |
| **安全** | 4 | `tirith_security`, `approval`, `path_security`, `osv_check` |
| **基础设施** | 6 | `process_registry`, `lazy_deps`, `budget_config` |

#### 3.4.3 执行环境子系统

`tools/environments/` 提供 7 种沙箱执行后端：

| 后端 | 文件 | 说明 |
|------|------|------|
| Local | `local.py` | 本地 shell |
| Docker | `docker.py` | Docker 容器 |
| SSH | `ssh.py` | 远程 SSH |
| Singularity | `singularity.py` | HPC 容器 |
| Modal | `modal.py` | Modal 云函数 |
| Daytona | `daytona.py` | Daytona 沙箱 |
| Vercel | `vercel_sandbox.py` | Vercel 沙箱 |

---

### 3.5 插件系统 (plugins/)

**加载器**: `hermes_cli/plugins.py` (59.9K)
**CLI 管理**: `hermes_cli/plugins_cmd.py` (54.1K)

#### 3.5.1 插件清单 (plugin.yaml)

```yaml
name: plugin-name
version: "1.0.0"
description: "Plugin description"
kind: standalone | backend | exclusive | platform | model-provider
requires_env:
  - name: API_KEY
    description: "API key for service"
provides_tools:
  - tool_name
hooks:
  - pre_tool_call
  - post_tool_call
```

#### 3.5.2 插件种类

| kind | 加载方式 | 用途 |
|------|---------|------|
| `standalone` | `plugins.enabled` 配置启用 | 通用功能扩展 |
| `backend` | 内建的自动加载 | 可替换后端（如图像生成） |
| `exclusive` | 专用发现系统 | 排他性提供者（如 memory） |
| `platform` | 内建的自动加载 | 消息平台适配器 |
| `model-provider` | 专用发现系统 | 推理后端 |

#### 3.5.3 插件发现源（优先级递增）

1. **Bundled** -- `<repo>/plugins/` (随项目发布)
2. **User** -- `~/.hermes/plugins/` (用户安装)
3. **Project** -- `./.hermes/plugins/` (需 `HERMES_ENABLE_PROJECT_PLUGINS`)
4. **Pip** -- 入口点 `hermes_agent.plugins`

#### 3.5.4 PluginContext 注册 API

| 方法 | 用途 |
|------|------|
| `register_tool()` | 注册工具到全局注册表 |
| `register_hook()` | 注册生命周期钩子 |
| `register_command()` | 注册斜杠命令 |
| `register_cli_command()` | 注册 CLI 子命令 |
| `register_platform()` | 注册平台适配器 |
| `register_image_gen_provider()` | 注册图像生成后端 |
| `register_video_gen_provider()` | 注册视频生成后端 |
| `register_web_search_provider()` | 注册 Web 搜索后端 |
| `register_context_engine()` | 注册上下文引擎 |
| `register_skill()` | 注册只读技能 |
| `inject_message()` | 注入消息到活跃对话 |
| `dispatch_tool()` | 通过注册表分发工具调用 |

#### 3.5.5 生命周期钩子（17 个）

```
pre_tool_call, post_tool_call,
transform_terminal_output, transform_tool_result, transform_llm_output,
pre_llm_call, post_llm_call,
pre_api_request, post_api_request,
on_session_start, on_session_end, on_session_finalize, on_session_reset,
subagent_stop,
pre_gateway_dispatch,
pre_approval_request, post_approval_response
```

#### 3.5.6 内建插件

| 插件 | 种类 | 功能 |
|------|------|------|
| `job-hunt` | standalone | 10 个求职斜杠命令 |
| `disk-cleanup` | standalone | 临时文件自动清理 |
| `spotify` | standalone | Spotify API 集成（7 工具） |
| `google_meet` | standalone | Google Meet 会议管线 |
| `teams_pipeline` | standalone | Teams 会议管线 |
| `memory` | exclusive | 记忆提供者发现 |
| `context_engine` | exclusive | 上下文引擎发现 |
| `hermes-achievements` | standalone | 成就追踪 |
| `kanban` | standalone | 多代理看板 |
| `image_gen/openai` | backend | OpenAI 图像生成 |
| `image_gen/xai` | backend | xAI 图像生成 |
| `platforms/google_chat` | platform | Google Chat 适配器 |
| `platforms/irc` | platform | IRC 适配器 |
| `platforms/teams` | platform | Teams 适配器 |
| `platforms/line` | platform | LINE 适配器 |

---

### 3.6 技能系统 (skills/)

**规模**: 25 个类别目录，168 个技能目录，79 个 SKILL.md 文件

#### 3.6.1 技能文件格式

```markdown
---
name: skill-name
description: "One-line description"
version: "1.0.0"
author: "Author Name"
license: MIT
platforms: [telegram, discord, cli]
metadata:
  hermes.tags: [category, subcategory]
  related_skills: [other-skill]
---

# Instructions

Markdown body with rules, workflows, and examples...
```

#### 3.6.2 技能类别

| 类别 | 子技能数 | 代表技能 |
|------|---------|---------|
| `apple/` | 5 | apple-notes, imessage, macos-computer-use |
| `autonomous-ai-agents/` | 4 | claude-code, codex, hermes-agent |
| `creative/` | 15 | architecture-diagram, excalidraw, manim-video, p5js |
| `data-science/` | 1 | jupyter-live-kernel |
| `devops/` | 3 | kanban-orchestrator, webhook-subscriptions |
| `github/` | 6 | github-code-review, github-pr-workflow |
| `media/` | 5 | spotify, youtube-content |
| `mlops/` | 7 | evaluation, huggingface-hub, training |
| `productivity/` | 9 | google-workspace, linear, notion, ocr-and-documents |
| `research/` | 5 | arxiv, polymarket, research-paper-writing |
| `software-development/` | 11 | test-driven-development, systematic-debugging, plan |

#### 3.6.3 技能加载管线

```
SKILL.md 文件
    │
    ▼
skills_tool.py: 解析 frontmatter + 检查前置条件
    │
    ▼
skills_guard.py: 安全约束检查
    │
    ▼
skills_hub.py: 技能编排和注入
    │
    ▼
Agent system prompt 注入
```

---

### 3.7 Job Hunt 求职流水线 (job-hunt/)

这是本项目的核心业务模块，实现自动化求职全流程。

#### 3.7.1 目录结构

```
job-hunt/
├── scripts/          # 35+ 流水线脚本（核心逻辑）
├── tests/            # 80+ 测试文件
├── data/
│   ├── candidate_profile.json         # 候选人档案
│   ├── job_sources.json               # 职位源注册表（5 个源）
│   ├── jobs_seen.jsonl                # 去重状态
│   ├── job_posting.schema.json        # 职位 JSON Schema
│   ├── material_stage_executors.json  # 5 个冻结阶段到脚本的映射
│   ├── jobs/                          # 标准化职位 JSON
│   └── raw_jobs/                      # 原始职位快照
├── outputs/
│   ├── resumes/       # 生成的简历/CV 产物
│   ├── logs/          # 报告、决策、执行日志
│   ├── fit_reports/   # 匹配评分报告
│   └── deployment/    # Cron/systemd 部署模板
├── prompts/           # 11 个提示模板
├── schemas/           # 8 个 JSON Schema
└── skills/            # 9 个 Hermes 技能定义
```

#### 3.7.2 两条核心管线

**管线 A: 职位发现与通知（Watch Cycle）**

```
/job_search_now 命令
    │
    ▼
run_job_watch_cycle.py 编排 5-8 步:
    │
    ├── 1. validate_job_sources.py     → 验证源配置安全性
    ├── 2. fetch_job_sources.py        → 读取/抓取原始快照
    ├── 3. extract_public_careers_jobs.py → 从公开招聘页提取职位块
    ├── 4. deduplicate_raw_jobs.py     → SHA-256 指纹去重
    ├── 5. [可选] 审计 + 质量门控
    ├── 6. run_batch_job_pipeline.py   → 批量标准化 + 启发式评分 + 排名
    ├── 7. render_telegram_job_notifications.py → 渲染通知消息
    └── 8. send_telegram_job_notifications.py   → 发送到 Telegram
```

**管线 B: 申请材料生成（Generate Pipeline）**

```
/job_generate <id> 命令（旧格式 /job_generate_<id> 仍兼容）
    │
    ▼
orchestrate_job_generate.py 编排 6 步:
    │
    ├── Step 1: route_user_job_action.py
    │     解析命令、解析别名、创建触发请求
    │
    ├── Step 2: prepare_approved_job_pipeline.py
    │     验证触发、派生 basename、写入清单
    │
    ├── Step 3: ensure_layer1_job + run_approved_job_material_pipeline.py
    │     Layer1 确保 data/jobs/<basename>.json 存在；
    │     Layer2 生成 4 个冻结材料阶段的执行命令
    │
    ├── Step 4: execute_approved_material_commands.py
    │     默认通过 Hermes oneshot 调用配置模型/provider 执行 Layer2:
    │     ┌─ Stage 1: job-fit-scorer          → outputs/logs/<basename>_fit_score.json
    │     ├─ Stage 2: resume-tailor           → model-generated .md
    │     │    export_resume_artifacts.py      → .docx
    │     │    export_resume_pdfs.py           → .pdf
    │     │    render_polished_resume_docx.py  → polished .docx
    │     │    export_polished_resume_pdfs.py  → polished .pdf
    │     ├─ Stage 3: application-tracker     → application_tracker_records.jsonl
    │     └─ Stage 4: submission-review-gate  → submission_decision.json
    │
    ├── Step 5: render_telegram_material_package.py
    │     收集产物、渲染文本摘要
    │
    └── Step 6: send_telegram_material_package.py
          发送文本 + 文档（默认 dry-run）
```

#### 3.7.3 候选人档案

**文件**: `data/candidate_profile.json`

| 字段 | 值 |
|------|-----|
| 姓名 | Hu Yaohua (胡耀华) |
| 学历 | 九州大学 院生 (修士) |
| 专业方向 | CV / ML / Edge AI |
| 论文 | 3 篇发表 |
| 实习经历 | Sony |
| 日语 | JLPT N2 |
| 英语 | TOEIC 750 |

#### 3.7.4 职位源配置

**文件**: `data/job_sources.json`

| 源 ID | 类型 | 平台 |
|--------|------|------|
| `wantedly_ai_ml_intern_japan` | manual_snapshot | Wantedly |
| `preferred_networks_internship` | public_url_html | Preferred Networks |
| `ntt_labs_internship_ai` | public_url_html | NTT Labs |
| `rakuten_engineering_internship` | manual_snapshot | Rakuten |
| `manual_job_snapshot_inbox` | manual_snapshot | 手动投递 |

每个源配置包含：`keywords`, `negative_keywords`, `locations`, `min_fit_score_for_notification`, 安全约束。

#### 3.7.5 Layer1/Layer2 冻结阶段

| 阶段 | 脚本 | 输入 | 输出 |
|------|------|------|------|
| Layer1. job-normalizer | `normalize_raw_job.py` | 原始 MD 快照 | `data/jobs/<basename>.json` |
| Layer2. job-fit-scorer | Hermes oneshot / local fallback | 标准化 JSON + 候选人档案 | 评分 (0-100) + 决策 |
| Layer2. resume-tailor | Hermes oneshot / local fallback | JSON + 档案 + 评分 | Japanese Markdown + DOCX/PDF |
| Layer2. application-tracker | Hermes oneshot / local fallback | 所有产物 | 追踪记录 |
| Layer2. submission-review-gate | Hermes oneshot / local fallback | 所有产物 | 审阅门控包 |

生产 `/job_generate <id>` 默认 `generation_backend: hermes`。`--generation-backend local`
只用于离线回归测试；旧的 local executor 产物不能视为 DeepSeek/Hermes 生成。验收时以
`outputs/logs/<action_id>_material_command_execution_report.json` 中的
`execution_backend`、`execution_mode`、`generation_backend` 为准。

Telegram 插件层不能同步等待完整 Hermes Layer2。四个 Hermes stage 的实际耗时可能超过
网关单轮响应窗口，旧实现会让用户 10-30 分钟没有任何反馈，甚至出现
`Script timed out after 600s`，同时已经启动的 Hermes/DeepSeek 子进程继续消耗 token。
`plugins/job-hunt/__init__.py` 现在对 `/job_generate` 立即返回 accepted ACK，把
`orchestrate_job_generate.py --send` 放入后台进程，并用后台 watcher 记录
`outputs/logs/job_generate_background_runs.jsonl`、stdout 和 stderr。最终材料文本由
Hermes/DeepSeek Layer2 生成；履歴書/職務経歴書 DOCX 与 PDF 由同一个 Layer2
`resume-tailor` 后处理链路导出后发送。插件只负责桥接和后台监督，不改 layer2 生成
逻辑，也不在 Telegram 发送阶段临时生成 PDF。

重复执行同一 action 时，orchestrator 会优先复用已有的成功执行报告，避免同一份材料反复
调用 DeepSeek。只有当
`outputs/logs/<action_id>_material_command_execution_report.json` 的 backend 与本次一致、
四个 Layer2 stage 全部 passed、且 expected outputs 没有 missing 时才会跳过 Step 4。
需要强制重跑模型时显式设置 `HERMES_JOB_HUNT_FORCE_REGENERATE=true` 或 CLI
`--force-regenerate`。

`Error: Script exited with code -15` 是 SIGTERM 退出信号。2026-05-17 排查中该错误来自
手动终止旧的 `/job_generate 4` 进程组以停止继续消耗 DeepSeek token，不代表 Hermes
或 layer2 业务逻辑本身失败。遇到 code -15 时先看后台生命周期日志、stderr 和
`<action_id>_material_command_execution_report.json`。

可覆盖的运行时变量：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `HERMES_JOB_HUNT_GENERATE_TIMEOUT` | computed | Telegram 插件外层 `/job_generate` 等待窗口 |
| `HERMES_JOB_HUNT_HERMES_STAGE_TIMEOUT` | `1200` | 单个 Hermes Layer2 stage 的超时 |
| `HERMES_JOB_HUNT_STEP_TIMEOUT` | `300` | 编排中非 Hermes 步骤的超时 |
| `HERMES_JOB_HUNT_HERMES_PROVIDER` | `deepseek` | Telegram `/job_generate` provider |
| `HERMES_JOB_HUNT_HERMES_MODEL` | `deepseek-v4-flash` | Telegram `/job_generate` model；高成本验收才覆盖为 `deepseek-v4-pro` |
| `HERMES_JOB_HUNT_FORCE_REGENERATE` | `false` | true 时忽略可复用执行报告并重新调用 Hermes |

真实 DeepSeek 验收使用 synthetic 数据，避免把真实候选人档案发送到外部 API：

```bash
export DEEPSEEK_API_KEY=...
python job-hunt/scripts/validate_deepseek_synthetic_e2e.py --model deepseek-v4-flash --keep-workspace
```

该校验器默认在 `job-hunt/outputs/synthetic_e2e_workspaces/` 下创建 synthetic workspace，
避免 Hermes `write_file` 命中 macOS `/var/folders` 系统临时目录写入限制，同时不发送真实
候选人档案或真实岗位资料。

**评分决策阈值**:

| 分数 | 决策 |
|------|------|
| >= 80 | `strong_match` -- 强烈推荐 |
| >= 65 | `possible_match` -- 可能匹配 |
| >= 50 | `weak_match` -- 弱匹配 |
| < 50 | `not_recommended` -- 不推荐 |

#### 3.7.6 安全边界

所有脚本和输出均强制包含三条安全边界：

1. **默认不提交** (`does_not_submit: true`)
2. **在最终提交前停止** (`allowed_to_submit: false`)
3. **任何提交操作需要明确的人工审批**

`execute_approved_material_commands.py` 中的 `FORBIDDEN_STAGES` 集合显式阻止：`live-submission-adapter`, `browser-apply-assistant`, `submit-application`。

---

### 3.8 Job Hunt 插件 (plugins/job-hunt/)

**文件**: `plugins/job-hunt/__init__.py`

将 `job-hunt/scripts/` 中的脚本桥接为 Telegram 斜杠命令。

**启用要求**: `job-hunt` 是 `standalone` 插件，默认不会自动加载。必须执行
`hermes plugins enable job-hunt`，或在 `~/.hermes/config.yaml` 中加入：

```yaml
plugins:
  enabled:
    - job-hunt
terminal:
  cwd: /Users/huyaohua/PycharmProjects/hermes-agent-job-hunt
```

Telegram BotCommand 不支持连字符，因此 Telegram 中实际显示和输入的是下划线命令，
例如 `/job_search_now`、`/job_generate 1`。Gateway 会把下划线规范化为插件内部
命令名（`job-search-now`, `job-generate`）。历史通知里生成的 `/job_generate_1`
格式由 `pre_gateway_dispatch` 钩子重写为稳定命令加参数，仍然可用。

#### 3.8.1 注册的命令

| Telegram 命令 | 插件命令 | 处理函数 | 对应脚本 | 说明 |
|------|------|---------|---------|------|
| `/job_search_start` | `/job-search-start` | `_handle_search_start` | `parse_job_search_command.py` | 启动后台 job-search watcher |
| `/job_search_stop` | `/job-search-stop` | `_handle_search_stop` | `parse_job_search_command.py` | 停止后台 job-search watcher |
| `/job_search_status` | `/job-search-status` | `_handle_search_status` | `parse_job_search_command.py` | 查看运行状态、PID、心跳和最近运行结果 |
| `/job_search_now` | `/job-search-now` | `_handle_search_now` | `parse_job_search_command.py` | 立即执行 watch cycle，并返回最新岗位摘要 |
| `/job_latest` | `/job-latest` | `_handle_latest` | `parse_job_search_command.py` | 查看当前或最近一次非空岗位摘要 |
| `/job_generate <id>` | `/job-generate <id>` | `_handle_generate` | `orchestrate_job_generate.py` | 生成申请材料 |
| `/job_track <id>` | `/job-track <id>` | `_handle_track` | `route_user_job_action.py` | 标记追踪 |
| `/job_ignore <id>` | `/job-ignore <id>` | `_handle_ignore` | `route_user_job_action.py` | 标记忽略 |
| `/job_defer <id>` | `/job-defer <id>` | `_handle_defer` | `route_user_job_action.py` | 标记延期 |
| `/job_review <id>` | `/job-review <id>` | `_handle_review` | `route_user_job_action.py` | 创建人工复核/材料触发请求 |

#### 3.8.2 命令分发流程

```
Telegram /job_search_now
    │
    ▼
hermes_cli/commands.py: is_gateway_known_command()
    │  下划线 → 连字符标准化
    │
    ▼
gateway/run.py: _handle_message()
    │  should_bypass_active_session() → True
    │
    ▼
plugins/job-hunt/__init__.py: _handle_search_now()
    │
    ▼
_run_script("parse_job_search_command.py", [...])
    │
    ▼
subprocess.run() → 脚本执行 → stdout JSON/文本
    │
    ▼
_format_status() → 格式化为 Telegram 消息
```

---

### 3.9 Trajectory 训练数据管线

#### 3.9.1 轨迹采集

- **触发**: `AIAgent.__init__(save_trajectories=True)`
- **格式**: ShareGPT (`{conversations: [{from, value}]}`)
- **输出**: `trajectory_samples.jsonl` (成功) / `failed_trajectories.jsonl` (失败)
- **隐私**: `ephemeral_system_prompt` 参数允许不持久化到轨迹的系统提示

#### 3.9.2 轨迹压缩

**文件**: `trajectory_compressor.py` (63.8K)

策略：保护首尾轮次，仅压缩中间区域，用摘要替换被压缩轮次。

#### 3.9.3 相关文件

| 文件 | 用途 |
|------|------|
| `agent/trajectory.py` | 轨迹保存、scratchpad 转换 |
| `trajectory_compressor.py` | 轨迹压缩工具 |
| `batch_runner.py` | 并行批处理 |
| `rl_training_tool.py` | RL 训练工具 |
| `rl_cli.py` | RL CLI |

---

## 4. 数据流架构

### 4.1 完整数据流图

```
┌─────────────────────────────────────────────────────────────────┐
│                    Job Hunt 数据流                               │
│                                                                  │
│  职位源 (5 个)                                                   │
│  ├── Wantedly (手动快照)                                         │
│  ├── Preferred Networks (公开页抓取)                              │
│  ├── NTT Labs (公开页抓取)                                       │
│  ├── Rakuten (手动快照)                                          │
│  └── 手动收件箱                                                   │
│       │                                                          │
│       ▼                                                          │
│  data/raw_jobs/<source>/<date>/*.md                              │
│       │                                                          │
│       ├── extract_public_careers_jobs.py → 提取职位块             │
│       │                                                          │
│       ▼                                                          │
│  deduplicate_raw_jobs.py → SHA-256 指纹去重                      │
│       │                                                          │
│       ├── data/jobs_seen.jsonl (去重状态)                         │
│       │                                                          │
│       ▼                                                          │
│  run_batch_job_pipeline.py → 标准化 + 评分 + 排名                │
│       │                                                          │
│       ├── data/jobs/*.json (标准化职位)                           │
│       ├── outputs/logs/*_fit_score.json (评分)                   │
│       │                                                          │
│       ▼                                                          │
│  render + send Telegram notifications                            │
│       │                                                          │
│       ▼                                                          │
│  用户操作: /job_generate_N                                       │
│       │                                                          │
│       ▼                                                          │
│  5 个冻结阶段 → outputs/resumes/*.md|.docx|.pdf                  │
│       │                                                          │
│       ▼                                                          │
│  Telegram 发送材料包 → 人工审阅 → 手动提交                       │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 脚本间通信协议

所有脚本通过 **磁盘上的 JSON 文件** 通信：

- **无共享内存状态**
- **无数据库连接**（除 SessionDB 的会话存储）
- **每个脚本读取特定输入文件，写入特定输出文件**
- **完全可审计、可重启**

---

## 5. 配置体系

### 5.1 三套配置加载器

| 加载器 | 使用场景 | 位置 |
|--------|---------|------|
| `load_cli_config()` | CLI 模式 | `cli.py` |
| `load_config()` | `hermes tools`, `hermes setup` | `hermes_cli/config.py` |
| 直接 YAML 加载 | Gateway 运行时 | `gateway/run.py` + `gateway/config.py` |

### 5.2 配置文件

| 文件 | 用途 |
|------|------|
| `~/.hermes/config.yaml` | 主配置文件 |
| `~/.hermes/.env` | API 密钥和秘密 |
| `cli-config.yaml.example` | 完整配置示例 (55.5K) |

### 5.3 配置段

| 段 | 说明 |
|----|------|
| `model` | 模型和 Provider 配置 |
| `agent` | Agent 行为参数 |
| `terminal` | 终端工具配置 |
| `compression` | 上下文压缩策略 |
| `gateway` | 网关配置 |
| `plugins` | 插件启用/禁用 |
| `security` | 安全策略 |
| `delegation` | 子代理委托配置 |
| `memory` | 记忆系统配置 |
| `cron` | 定时任务配置 |
| `profiles` | 多 Profile 配置 |

---

## 6. 安全模型

### 6.1 认证层

| 机制 | 位置 | 说明 |
|------|------|------|
| Provider 认证 | `hermes_cli/auth.py` | 20+ Provider 的 OAuth/API Key 管理 |
| DM 配对码 | `gateway/pairing.py` | 8 位码，1 小时过期，5 次失败锁定 |
| 白名单 | Gateway config | `allowed_users` 配置 |
| 命令访问控制 | `gateway/slash_access.py` | Admin/用户分级权限 |

### 6.2 工具安全

| 机制 | 说明 |
|------|------|
| `approval.py` | 危险命令人工审批流 |
| `path_security.py` | 文件路径安全检查 |
| `url_safety.py` | URL SSRF 防护 |
| `tirith_security.py` | 安全策略扫描 |
| `osv_check.py` | 依赖漏洞检查 |

### 6.3 Job Hunt 安全边界

- `does_not_submit: true` -- 所有输出默认不提交
- `allowed_to_submit: false` -- 显式禁止自动提交
- `FORBIDDEN_STAGES` -- 阻止 `live-submission-adapter`, `browser-apply-assistant`, `submit-application`
- 源验证 (`validate_job_sources.py`) -- 无凭据、无自动申请、遵守 robots.txt

---

## 7. 测试体系

### 7.1 规模

- **1,105 个 Python 测试文件**
- **900+ 测试文件**
- **80+ Job Hunt 测试文件**

### 7.2 目录结构

| 目录 | 测试范围 |
|------|---------|
| `tests/` | 顶层模块 (61 文件) |
| `tests/agent/` | Agent 内部 |
| `tests/cli/` | CLI |
| `tests/gateway/` | 消息网关 |
| `tests/plugins/` | 插件系统 |
| `tests/tools/` | 工具实现 |
| `tests/skills/` | 技能系统 |
| `tests/integration/` | 集成测试 (标记，默认跳过) |
| `tests/e2e/` | 端到端测试 |
| `job-hunt/tests/` | Job Hunt 流水线 (80+ 文件) |

### 7.3 测试隔离 (conftest.py)

严格的测试隔离机制（966 行）：

1. **无凭据环境变量** -- 所有 Provider 凭据在每个测试前清除
2. **隔离 HERMES_HOME** -- 每个测试使用临时目录
3. **确定性运行时** -- TZ=UTC, LANG=C.UTF-8, PYTHONHASHSED=0
4. **模块级状态重置** -- 清除所有可变全局状态
5. **活跃系统保护** -- 拦截 `os.kill`, `subprocess.run` 等，阻止杀死非测试进程
6. **全局超时** -- 每个测试 30 秒 SIGALRM

### 7.4 pytest 配置

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["integration: requires external services"]
addopts = "-m 'not integration' -n auto"
```

---

## 8. 部署架构

### 8.1 Job Hunt 部署模板

**位置**: `job-hunt/outputs/deployment/`

| 文件 | 用途 |
|------|------|
| `hermes_job_hunt_watch.cron` | Cron 调度 |
| `hermes-job-hunt-watch.service` | systemd 服务 |
| `hermes-job-hunt-watch.service` | systemd 定时器 |
| `hermes_job_hunt_watch.env.template` | 环境变量模板 |
| `watch_cycle_scheduler_handoff_runbook.md` | 运维手册 |

### 8.2 Gateway 服务管理

| 平台 | 安装方式 |
|------|---------|
| Linux | systemd (`hermes gateway install`) |
| macOS | launchd (`hermes gateway install`) |
| Windows | Windows Service (`hermes gateway install`) |
| Docker | Dockerfile + docker-compose.yml |
| WSL | systemd |
| Termux | termux-service |

### 8.3 环境变量

| 变量 | 用途 |
|------|------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API Token |
| `TELEGRAM_CHAT_ID` | 目标聊天 ID |
| `HERMES_HOME` | 配置和数据目录 (默认 `~/.hermes/`) |
| `HERMES_PROFILE` | Profile 名称 |
| `HERMES_ENABLE_PROJECT_PLUGINS` | 启用项目级插件 |

### 8.4 最小启动步骤

```bash
cd /Users/huyaohua/PycharmProjects/hermes-agent-job-hunt
source .venv/bin/activate
hermes plugins enable job-hunt
hermes gateway setup
hermes gateway run --replace
```

配置入口尽量集中在两个用户文件：

- `~/.hermes/config.yaml`: 非密钥配置，例如 `plugins.enabled` 和 `terminal.cwd`
- `~/.hermes/.env`: 密钥和 token，例如 `TELEGRAM_BOT_TOKEN`

推荐的最小 `config.yaml` 片段：

```yaml
plugins:
  enabled:
    - job-hunt
terminal:
  cwd: /Users/huyaohua/PycharmProjects/hermes-agent-job-hunt
```

`/job_search_start` 是用户侧最简后台入口：它会通过
`scripts/control_job_search_runtime.py start` 启动 detached watcher，默认每 3600 秒
执行一轮真实搜索，并在配置了 `TELEGRAM_CHAT_ID` 时推送 Telegram digest。状态文件
`outputs/logs/job_search_runtime_state.json` 会记录 `watcher_pid`、`watcher_alive`、
`last_heartbeat_at`、`last_run_at` 和最近结果。需要停止时使用 `/job_search_stop`。

Telegram `/job_search_now` 现在是手动实时搜索入口：插件会传
`--allow-network`，执行一轮联网抓取和排名，但仍保持 Telegram delivery dry-run，
结果直接作为命令回复返回。这样不会额外推送 digest，也不会提交申请。手动验证：

```bash
cd /Users/huyaohua/PycharmProjects/hermes-agent-job-hunt/job-hunt
../.venv/bin/python scripts/parse_job_search_command.py /job_search_now \
  --workspace . \
  --allow-network
```

本地直接运行 `run_job_watch_cycle.py` 时仍需显式加 `--allow-network`；需要真实发送
时显式加 `--send-telegram`。

Ranking 展示有一个防空覆盖快照：

- 当前轮次：`outputs/logs/job_ranking_gate_decision.json`
- 最近非空轮次：`outputs/logs/job_ranking_gate_decision_last_nonempty.json`
- 当前短别名：`outputs/logs/telegram_action_alias_map.json`
- 最近非空短别名：`outputs/logs/telegram_action_alias_map_last_nonempty.json`

因此当本轮岗位都已去重、没有新通知时，`/job_latest` 会显示最近一次非空岗位，
并保持 `/job_generate 1`、`/job_track 1` 等动作可用。分页入口为
`/job_latest 2`，全量紧凑入口为 `/job_latest all`；digest 中的 `...and N more`
会直接提示这两个入口。

`/job_generate <id>` 是后台执行链路：Telegram 插件立即 ACK，然后 detached
子进程运行 `orchestrate_job_generate.py --send`。生产路径必须保持
`generation_backend: hermes`，由 Hermes 调用配置的 DeepSeek provider/model 完成
Layer2 分析与正文生成；DOCX/PDF 导出属于同一 Layer2 `resume-tailor` 后处理步骤，
Telegram delivery 只发送已经生成的材料包。进度通过
`outputs/logs/job_generate_<id>_progress.jsonl` 记录，
并由插件监控线程发送 Telegram 阶段消息：5-35% 为 Layer1->Layer2 桥接，35-80%
为四个冻结 Layer2 stage，90% 为材料包渲染，95-100% 为 Telegram 发送。
修改该插件或 `.env` 后必须重启 `hermes gateway run --replace`，否则 bot 进程继续
使用启动时 import 的旧模块。正确 ACK 会包含 progress updates；只说 package when
ready 的 ACK 表示仍是旧插件。

2026-05-17 `/job_generate 4` 的验收事故说明：fit score/report、履歴書/職務経歴書
DOCX/PDF 已由 Hermes/DeepSeek Layer2 链路生成，但最终没有回到 Telegram，是
delivery 失败而不是生成失败。`telegram_material_delivery_report.json` 是第一诊断文件。若
`telegram_material_package.json` 已存在且 `document_count` 为 8，应优先用
`send_telegram_material_package.py --send` 补发现有 package；该补发路径不会重新调用
Hermes 或消耗 DeepSeek token。成功验收形态是 `sent_count: 9`、`text_delivered:
true`、`document_delivered_count: 8`。
delivery 目标优先使用 `TELEGRAM_CHAT_ID`，缺失时兼容 Hermes gateway setup 写入的
`TELEGRAM_HOME_CHANNEL`。

开发和排障步骤见：

```text
job-hunt/docs/job_search_runtime_fix_runbook.md
```

---

## 附录 A: 关键文件索引

| 文件 | 行数 | 用途 |
|------|------|------|
| `run_agent.py` | 16,081 | Agent 核心引擎 |
| `gateway/run.py` | 16,500+ | Gateway 编排器 |
| `hermes_cli/main.py` | 12,176 | CLI 入口 |
| `hermes_cli/commands.py` | ~1,800 | 命令注册表 |
| `hermes_cli/plugins.py` | ~1,500 | 插件加载器 |
| `hermes_cli/config.py` | ~6,000 | 配置管理 |
| `hermes_cli/auth.py` | ~5,500 | 认证管理 |
| `gateway/platforms/base.py` | ~3,000+ | 平台适配器基类 |
| `gateway/session.py` | ~1,400 | 会话管理 |
| `tools/registry.py` | ~500 | 工具注册中心 |
| `plugins/job-hunt/__init__.py` | ~400 | Job Hunt 插件 |
| `job-hunt/scripts/orchestrate_job_generate.py` | ~300 | 材料生成编排 |
| `job-hunt/scripts/run_job_watch_cycle.py` | ~400 | Watch Cycle 编排 |

## 附录 B: Telegram 命令速查

| 命令 | 功能 |
|------|------|
| `/help` | 显示帮助 |
| `/new` | 新建会话 |
| `/reset` | 重置当前会话 |
| `/stop` | 停止运行中的 Agent |
| `/status` | 查看 Agent 状态 |
| `/model <name>` | 切换模型 |
| `/queue <msg>` | 排队消息 |
| `/steer <msg>` | 注入中途提示 |
| `/job_search_start` | 启动后台搜索 watcher |
| `/job_search_stop` | 停止后台搜索 watcher |
| `/job_search_status` | 查看搜索状态、PID 和心跳 |
| `/job_search_now` | 立即执行搜索并返回岗位摘要 |
| `/job_latest` | 查看当前或最近非空职位 |
| `/job_generate <id>` | 生成申请材料 |
| `/job_track <id>` | 标记追踪 |
| `/job_ignore <id>` | 标记忽略 |
| `/job_defer <id>` | 标记延期 |
| `/job_review <id>` | 创建复核请求 |

> Telegram 实际菜单使用下划线：`/job_search_now`、`/job_latest`、
> `/job_generate <id>`、`/job_track <id>` 等。连字符形式是插件内部规范名；
> 旧格式 `/job_generate_<id>` 继续兼容。

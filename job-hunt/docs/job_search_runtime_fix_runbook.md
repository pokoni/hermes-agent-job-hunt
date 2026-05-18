# Job Search Runtime Fix Runbook

本文件是 job-hunt Telegram 链路的统一开发修复手册。后续排查
`/job_search_*`、`/job_latest`、`/job_generate` 相关问题时，以这里的根因、
修复记录、验证命令和错误指纹为准，避免 `TECHNICAL_DOC.md`、README 和阶段文档
之间出现口径漂移。

## 背景

2026-05-16 的 Telegram 实测现象：

- `/job_search_status` 返回 `Active: yes`，但没有持续岗位推送。
- `/job_search_now` 与 `/job_latest` 返回 `Matched jobs: 0`。
- `/job_generate 12` 只返回 pipeline step 状态和 `Telegram delivery: dry-run`，
  没有真正运行 Hermes/模型材料生成，也没有把履历书/职务経歴書路径返回给用户。
- `/job_generate <id>` 只有 DOCX 没有 PDF，通常是 `resume-tailor` 的 PDF export
  步骤被系统缺少 LibreOffice 卡住，或者 Telegram 发送时只拿到了 DOCX。
- 用户按 Claude 文档完成 gateway 配置后，命令能进入插件，但真实工作链路没有跑通。

结论：这不是单一配置问题，而是运行控制层、材料生成执行层和结果展示层的实现
语义不完整。

## 根因

### 1. `/job_search_start` 只写状态

修复前，`scripts/control_job_search_runtime.py start` 只把
`outputs/logs/job_search_runtime_state.json` 的 `enabled` 写成 `true`，不会启动
后台循环，也不会触发网络抓取或 Telegram 发送。因此状态看起来是 active，但不会
自动产生岗位推送。

### 2. 空轮次覆盖了可展示岗位

`scripts/run_batch_job_pipeline.py` 只对 `deduplicate_raw_jobs` 的 `new_jobs` 排名。
当本轮抓到的岗位都已经记录在 `data/jobs_seen.jsonl` 中时，本轮排名为空，并覆盖
`outputs/logs/job_ranking_gate_decision.json`。随后 `/job_latest` 只能展示 0 条。

这个行为对通知是合理的：不能重复推送旧岗位。但对“查看最新可操作岗位”不合理：
用户仍然需要看到上一轮非空结果，并继续使用 `/job_generate 1`、`/job_track 1`
等动作。

### 3. `/job_generate` 执行后端口径错误

修复前，`scripts/orchestrate_job_generate.py` 的第 4 步注释写着
“Execute material commands with local executors”，但实际调用
`scripts/execute_approved_material_commands.py` 时没有传入 `--use-local-executors`。
因此 5 个材料阶段都会落入 `pending_supervised_skill_execution`，只记录 slash
命令，不会生成 `outputs/resumes/*_resume_ja.docx`、`*_cv_ja.docx` 等材料。

随后为了让本地测试跑通，链路曾默认走 local executor。这会生成文件，但不会产生
DeepSeek/Hermes API token usage：`score_job_fit.py` 是本地 heuristic scorer，
`generate_resume_markdown.py` 明确是本地模板生成器。因此这类产物只能标记为
`generation_backend: local_executor`，不能宣称是 Hermes/DeepSeek 生成。

同时，`plugins/job-hunt/__init__.py` 的 `_format_orchestration_status()` 只展示
pipeline steps，不展示 `render_telegram_material_package.py` 产出的材料包消息、
`document_files` 或发送错误。用户看到的是“6 步 passed + dry-run”，但真实材料
为空。

当前修复后：

- `/job_generate <id>` 插件层立即返回 accepted ACK，不再同步阻塞 gateway turn。
  真实 `orchestrate_job_generate.py --send` 在后台进程中继续运行。
- `/job_generate <id>` 通过插件触发时默认请求真实 Telegram delivery。
- 编排器默认使用 `generation_backend: hermes`，通过 Hermes oneshot 调用配置的
  model/provider 运行 Layer2。
- Telegram 默认 Hermes 模型为 `deepseek-v4-flash`；只有高成本验收才显式覆盖为
  `deepseek-v4-pro`。
- 重复同一 action 时优先复用已有成功的 material execution report，避免重复消耗
  DeepSeek token；需要重跑时显式设置 `HERMES_JOB_HUNT_FORCE_REGENERATE=true`。
- `--generation-backend local` 仅作为显式 offline/test fallback；`record` 仅用于
  监督式占位调试。
- Layer1 负责确保 `data/jobs/<basename>.json` 存在；Layer2 默认只包含
  `job-fit-scorer`、`resume-tailor`、`application-tracker`、
  `submission-review-gate`。
- `resume-tailor` 的正文必须先由 Hermes/模型写出
  `outputs/resumes/<basename>_resume_ja.md` 和
  `outputs/resumes/<basename>_cv_ja.md`；本地脚本只负责把这些 Markdown 转成
  DOCX/PDF，不再偷偷用本地模板替代模型正文。
- 编排器最终 JSON 会包含 `material_package`、`material_message`、
  `document_files`、`document_count`、`delivery_report` 和
  `material_execution_results`。
- 插件回复优先展示材料包摘要和文档路径；如果产物为 0，会明确输出 diagnostics。
- PDF export 现在有日文 CID fallback，不再依赖本机 LibreOffice 才能生成可读 PDF。

## 修复后的架构

```text
Telegram /job_search_start
  -> plugins/job-hunt/__init__.py
  -> scripts/parse_job_search_command.py
  -> scripts/control_job_search_runtime.py start
  -> detached watch-loop process
  -> scripts/run_job_watch_cycle.py
  -> fetch/dedup/rank/render/send
```

```text
Telegram /job_search_now
  -> synchronous run-now
  -> Telegram plugin passes --allow-network and keeps Telegram delivery dry-run
  -> current ranking if non-empty
  -> else last non-empty ranking fallback
```

```text
Telegram /job_latest
  -> read current watch report
  -> current ranking if non-empty; supports /job_latest 2 and /job_latest all
  -> else last non-empty ranking fallback
```

```text
Telegram /job_generate <id>
  -> plugins/job-hunt/__init__.py
  -> immediate accepted ACK
  -> detached background process
  -> scripts/orchestrate_job_generate.py --send
  -> route_user_job_action.py
  -> prepare_approved_job_pipeline.py
  -> ensure_layer1_job: data/jobs/<basename>.json
  -> run_approved_job_material_pipeline.py --layer2-only
  -> execute_approved_material_commands.py --execute --execution-backend hermes
  -> Hermes oneshot Layer2: score / resume-tailor / tracker / review-gate
  -> local DOCX/PDF conversion from Hermes-generated Markdown
  -> render_telegram_material_package.py
  -> send_telegram_material_package.py --send
  -> Telegram text + DOCX/PDF documents, or explicit delivery config error
```

## 文件职责

| 文件 | 职责 |
|------|------|
| `scripts/control_job_search_runtime.py` | 控制 start/stop/status/run-now/watch-loop；维护 watcher PID、心跳、最后运行结果 |
| `scripts/run_job_watch_cycle.py` | 执行单轮 validate/fetch/extract/dedup/rank/render/send |
| `scripts/run_batch_job_pipeline.py` | 排名本轮新岗位；写入当前 ranking；当本轮非空时刷新 last non-empty ranking |
| `scripts/render_telegram_job_notifications.py` | 渲染 Telegram 通知与短别名；当本轮非空时刷新 last non-empty alias map |
| `scripts/parse_job_search_command.py` | 把 Telegram 搜索命令转成人类可读消息；当前为空时回退 last non-empty |
| `scripts/route_user_job_action.py` | 解析 `/job_generate 1` 等动作；当前别名为空时回退 last non-empty alias/ranking |
| `scripts/orchestrate_job_generate.py` | 编排 `/job_generate` 全链路；默认使用 Hermes backend；返回材料包与 delivery 报告 |
| `scripts/execute_approved_material_commands.py` | 执行 Layer2 材料阶段；支持 `hermes`、`local`、`record` 三种后端 |
| `scripts/render_telegram_material_package.py` | 收集 `outputs/resumes/` 产物并渲染 Telegram 材料包 |
| `scripts/send_telegram_material_package.py` | dry-run 或真实发送材料包；真实发送需要 `TELEGRAM_BOT_TOKEN` 与 `TELEGRAM_CHAT_ID` |
| `scripts/validate_deepseek_synthetic_e2e.py` | 使用 synthetic profile/job 做真实 DeepSeek API 验收，工作区位于 `outputs/synthetic_e2e_workspaces/`，避免泄露真实资料和 macOS `/var/folders` 写入限制 |
| `skills/resume-tailor/scripts/export_resume_pdfs.py` | 生成普通 PDF；优先 LibreOffice，缺失时走日文 CID fallback |
| `skills/resume-tailor/scripts/export_polished_resume_pdfs.py` | 生成 polished PDF；优先 LibreOffice，缺失时走日文 CID fallback |
| `plugins/job-hunt/__init__.py` | Hermes gateway 插件命令桥接 |

## 新增/变更状态文件

| 路径 | 用途 |
|------|------|
| `outputs/logs/job_search_runtime_state.json` | runtime 状态、PID、心跳、最后运行结果 |
| `outputs/logs/job_search_watch_loop.log` | 后台 watcher stdout/stderr |
| `outputs/logs/job_ranking_gate_decision.json` | 当前轮次 ranking |
| `outputs/logs/job_ranking_gate_decision_last_nonempty.json` | 最近一次非空 ranking 快照 |
| `outputs/logs/telegram_action_alias_map.json` | 当前轮次短别名 |
| `outputs/logs/telegram_action_alias_map_last_nonempty.json` | 最近一次非空短别名快照 |
| `outputs/logs/telegram_notifications_last_nonempty.jsonl` | 最近一次非空通知快照 |
| `outputs/logs/job_generate_background_runs.jsonl` | `/job_generate` 后台进程 started/finished/timed_out 生命周期 |
| `outputs/logs/job_generate_<id>_background_stdout.log` | 后台 orchestrator stdout |
| `outputs/logs/job_generate_<id>_background_stderr.log` | 后台 orchestrator stderr |
| `outputs/logs/<action_id>_material_command_execution_report.json` | `/job_generate` 材料阶段执行详情；检查 local executor 是否真的跑了 |
| `outputs/logs/telegram_material_package.json` | `/job_generate` 最近一次材料包摘要、`document_files`、本地 Markdown 审计产物 |
| `outputs/logs/telegram_material_delivery_report.json` | `/job_generate` Telegram 文本/文档发送结果；含缺失配置提示 |
| `outputs/resumes/<job_basename>_*` | 生成的履历书、职务経歴書、Markdown 中间件、DOCX、可选 PDF |

## 执行步骤

### 1. 配置插件和工作目录

`~/.hermes/config.yaml` 至少包含：

```yaml
plugins:
  enabled:
    - job-hunt
terminal:
  cwd: /Users/huyaohua/PycharmProjects/hermes-agent-job-hunt
```

### 2. 配置 Telegram secrets

`~/.hermes/.env` 至少包含：

```env
TELEGRAM_BOT_TOKEN=123456:your-bot-token
TELEGRAM_CHAT_ID=123456789
```

`TELEGRAM_BOT_TOKEN` 用于 gateway 收消息；`TELEGRAM_CHAT_ID` 用于 job-hunt
脚本主动推送岗位 digest 和材料包。Hermes gateway setup 常写入
`TELEGRAM_HOME_CHANNEL`；现在 job-hunt 会在缺少 `TELEGRAM_CHAT_ID` 时自动回退使用
`TELEGRAM_HOME_CHANNEL`。

### 3. 启动 gateway

```bash
cd /Users/huyaohua/PycharmProjects/hermes-agent-job-hunt
source .venv/bin/activate
hermes plugins enable job-hunt
hermes gateway run --replace
```

改动插件代码或 `~/.hermes/.env` 后必须重启 gateway。Telegram bot 进程会在启动时
import plugin；不重启时会继续使用旧逻辑。验收 ACK 应包含：

```text
I will send progress updates and the DOCX/PDF package when ready.
```

如果仍然只看到：

```text
I will send the DOCX/PDF package when ready.
```

说明当前 gateway 还没有加载 progress 版插件。

### 4. 在 Telegram 中启动后台搜索

```text
/job_search_start
```

期望返回包含：

```text
Job search started: background watcher running.
Watcher PID: <pid>
Network fetch: yes
Telegram send: yes
```

默认后台轮询间隔是 3600 秒。`/job_search_start` 会立即执行第一轮，然后按间隔
继续执行。

### 5. 查看运行状态

```text
/job_search_status
```

重点检查：

- `Active: yes`
- `Watcher PID: ...`
- `Watcher alive: yes`
- `Telegram send: yes`
- `Network fetch: yes`
- `Last status: passed`
- `Watcher log: outputs/logs/job_search_watch_loop.log`

### 6. 手动跑一轮 dry-run

```text
/job_search_now
```

在 Telegram 中，这个命令现在会执行一轮联网抓取和排名，但仍保持 Telegram delivery
dry-run：结果直接作为命令回复返回，不额外发送 digest。这样用户每次手动搜索都能
触达新增公开来源，而不是只在旧快照上重复打分。

如果在本地 CLI 直接调用 `parse_job_search_command.py`，需要显式传
`--allow-network` 才会联网：

```bash
cd /Users/huyaohua/PycharmProjects/hermes-agent-job-hunt
.venv/bin/python job-hunt/scripts/parse_job_search_command.py /job_search_now \
  --workspace job-hunt \
  --allow-network
```

### 7. 查看最新可操作岗位

```text
/job_latest
```

只显示第一页时，如果还有更多岗位，会出现：

```text
...and <n> more. Use /job_latest all to show every job, or /job_latest 2 for the next page.
```

可用入口：

```text
/job_latest 2
/job_latest all
```

`/job_latest all` 是紧凑全量列表：每行保留编号、分数和标题。编号仍是操作入口，
例如 `/job_generate 17`、`/job_track 17`。

如果当前轮次没有新岗位，但历史有非空结果，会显示：

```text
Current cycle produced no new matched jobs; showing last non-empty results from ...
```

此时 `/job_generate 1` 等动作仍然可用，因为系统会回退到
`telegram_action_alias_map_last_nonempty.json`。

### 8. 生成申请材料并推送 Telegram

```text
/job_generate 1
```

期望第一条回复立即包含：

```text
Accepted /job_generate 1. Generation is running in the background with Hermes deepseek/deepseek-v4-flash ...
```

后台完成后，`send_telegram_material_package.py --send` 会继续把材料包发送到 Telegram。
期望最终材料消息包含：

```text
Application Materials Ready
Generated document count: <n>
Telegram document file paths:
  - 履歴書 DOCX: outputs/resumes/<job>_resume_ja.docx
  - 職務経歴書 DOCX: outputs/resumes/<job>_cv_ja.docx
  - 履歴書 PDF: outputs/resumes/<job>_resume_ja.pdf
  - 職務経歴書 PDF: outputs/resumes/<job>_cv_ja.pdf
Telegram delivery: sent
Human review required: yes
Auto-submit: disabled
```

生成过程中还应主动发送阶段进度，而不是让用户等待几十分钟无反馈。期望能看到类似：

```text
/job_generate progress: 5% - Job material generation accepted.
/job_generate progress: 35% - Layer2 material executor started.
/job_generate progress: 46% - Layer2 stage 1/4 finished: job-fit-scorer
/job_generate progress: 80% - Layer2 material executor finished.
/job_generate progress: 90% - Telegram material package rendered.
/job_generate progress: 100% - Telegram material package delivered.
```

对应进度文件是：

```text
outputs/logs/job_generate_<id>_progress.jsonl
```

百分比是粗粒度检查点，不是 token 级进度：

| 区间 | 含义 |
|------|------|
| 5-35% | 解析 `/job_generate`、准备 trigger、确保 Layer1 normalized job、生成 Layer2 command plan |
| 35-80% | 运行冻结 Layer2：fit score、resume tailor、tracker、review gate |
| 90% | 渲染 `telegram_material_package.json` |
| 95-100% | 真实发送 Telegram 摘要与 DOCX/PDF |

如果再次发送同一个 `/job_generate <id>` 且后台进程仍在运行，期望回复：

```text
/job_generate <id> is already running in the background ...
```

如果 `TELEGRAM_CHAT_ID` 未配置，材料仍会在本地产生，回复会显示 `Delivery
errors`，并保留 `Telegram document file paths`。此时补齐 `~/.hermes/.env` 后重新执行
`/job_generate <id>`。

### 8.1 编号与指纹

`/job_generate <id>` 里的 `<id>` 是当前轮次的短别名，不是永久编号。
如果后续重新跑了搜索轮次，编号可能漂移。

回溯时优先看这三个文件：

- `outputs/logs/telegram_action_alias_map.json`
- `outputs/logs/telegram_action_alias_map_last_nonempty.json`
- `outputs/logs/<action_id>_pipeline_trigger_request.json`

如果用户拿着旧编号问“为什么不是那条岗位”，先核对 alias map 里的 `title`、
`raw_job_path` 和 `resolved_commands.generate`，不要只看 Telegram 消息里的数字。

### 8.2 PDF 产物判断

`/job_generate` 的最终目标不是返回 Markdown，而是返回可发送的 DOCX/PDF 材料包。
如果消息里只看到 DOCX 没有 PDF，优先检查：

1. `outputs/logs/<action_id>_material_command_execution_report.json`
2. `outputs/resumes/<job_basename>_pdf_export_manifest.json`
3. `outputs/logs/telegram_material_package.json`

现在 PDF export 已增加日文 CID stdlib fallback（`cid_japanese_fallback`），不再依赖
LibreOffice 才能产出可读 PDF。这个 fallback 仍然属于 Layer2 的 `resume-tailor`
后处理步骤，不是 Telegram 发送阶段在“顺手转一份”。所以只要 DOCX 已存在，PDF
也应当出现；若没出现，多半是前一步材料生成没有跑完，或者 export 阶段本身失败，
而不是系统缺软件。

### 8.3 Hermes/DeepSeek 产物判断

不要用“文件存在”判断是否由 DeepSeek 生成。必须看执行报告：

```bash
jq '{execution_backend, use_local_executors, results: [.execution_results[] | {stage, execution_mode, generation_backend, status, hermes_provider, hermes_model}]}' \
  outputs/logs/<action_id>_material_command_execution_report.json
```

合格的 DeepSeek/Hermes Layer2 运行应满足：

- `execution_backend: "hermes"`
- `use_local_executors: false`
- 每个 Layer2 stage 都是 `execution_mode: "hermes_oneshot"`
- 每个 Layer2 stage 都是 `generation_backend: "hermes"`
- `resume-tailor` 的 post-processing 只允许把模型生成的 Markdown 转为 DOCX/PDF

如果看到 `local_executor`、`local_heuristic_fit_scorer_v1` 或
`generate_resume_markdown`，那是离线 fallback/test 产物，不是 DeepSeek 产物。

### 8.4 `/job_generate` 回复 `Script timed out after 600s`

这个错误通常不是 DeepSeek 没跑，而是 Telegram 插件层的外层等待时间太短。
当外层在 600 秒处先返回错误时，内层 Hermes/DeepSeek 子进程可能已经开始并继续消耗
token，随后才把 fit report、resume、tracker、review gate 写完。

已修复的行为：

- `/job_generate` 不再同步等待完整 Hermes Layer2，而是立即 ACK 后台运行
- 同一 `<id>` 已在后台运行时，不会再次启动第二个 Hermes 子进程
- 后台等待时间按 Hermes stage 预算计算，并允许通过环境变量覆盖
- 后台超时时会终止整个子进程组，避免继续烧 token
- 编排器会复用已有成功执行报告，避免重复调用 DeepSeek

可调参数：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `HERMES_JOB_HUNT_GENERATE_TIMEOUT` | computed | `/job_generate` 外层等待窗口 |
| `HERMES_JOB_HUNT_HERMES_STAGE_TIMEOUT` | `1200` | 单个 Layer2 Hermes stage 超时 |
| `HERMES_JOB_HUNT_STEP_TIMEOUT` | `300` | 编排非 Hermes 步骤超时 |
| `HERMES_JOB_HUNT_HERMES_PROVIDER` | `deepseek` | `/job_generate` provider |
| `HERMES_JOB_HUNT_HERMES_MODEL` | `deepseek-v4-flash` | `/job_generate` model；仅高成本验收覆盖为 `deepseek-v4-pro` |
| `HERMES_JOB_HUNT_FORCE_REGENERATE` | `false` | true 时忽略可复用执行报告并重新调用 Hermes |

### 8.4.1 `/job_generate` 回复 `Error: Script exited with code -15`

`code -15` 是 SIGTERM。2026-05-17 的实测中，这个错误来自手动终止已经运行约
30 分钟的旧 `/job_generate 4` 进程组，用于停止继续消耗 DeepSeek token；它不是
Hermes/Layer2 业务失败的直接证据。

排查顺序：

1. 查看 `outputs/logs/job_generate_background_runs.jsonl`，确认是否是
   `timed_out` 或人工终止。
2. 查看 `outputs/logs/job_generate_<id>_background_stderr.log`。
3. 查看 `outputs/logs/<action_id>_material_command_execution_report.json`，确认是否已经
   写入 `execution_backend: hermes` 和各 stage 状态。
4. 如果报告完整且可复用，重新执行同一 `/job_generate <id>` 应复用报告并发送材料包；
   只有需要重做模型分析时才设置 `HERMES_JOB_HUNT_FORCE_REGENERATE=true`。

排查时优先看 `<action_id>_material_command_execution_report.json`，确认
`execution_backend`、`execution_mode`、`generation_backend` 和 `hermes_model/provider`
是否已经写入。

### 8.5 Telegram 发送失败的判读

如果 `telegram_material_delivery_report.json` 显示：

```text
Real send requested but TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID/TELEGRAM_HOME_CHANNEL are required.
```

说明不是材料没生成，而是 gateway 运行时没有加载 `.env`，或 `.env` 缺少 Telegram
delivery 目标。
这时需要：

1. 把 `TELEGRAM_BOT_TOKEN` 和 `TELEGRAM_CHAT_ID` 写入 `~/.hermes/.env`，或确认
   `TELEGRAM_HOME_CHANNEL` 已存在
2. 重启 `hermes gateway run --replace`
3. 再执行 `/job_generate <id>`

不要只盯着 Telegram 消息里的 `Step 6 failed`，真正原因通常在
`outputs/logs/telegram_material_delivery_report.json` 里。

如果报告显示 `missing_telegram_configuration: false` 但每个 delivery 都类似：

```text
<urlopen error [Errno 8] nodename nor servname provided, or not known>
```

说明配置已加载，但当前运行环境不能访问 Telegram API。2026-05-17 的
`/job_generate 4` 实测就是这个形态：Layer2/Hermes 已经生成 8 个 DOCX/PDF，发送步骤
因网络/DNS 失败，导致用户几小时没有收到材料。修复或放开网络后，优先只补发已渲染
package，避免重新消耗 DeepSeek token：

```bash
cd /Users/huyaohua/PycharmProjects/hermes-agent-job-hunt
TELEGRAM_CHAT_ID=<target-chat-id> python job-hunt/scripts/send_telegram_material_package.py \
  --workspace job-hunt \
  --package outputs/logs/telegram_material_package.json \
  --report outputs/logs/telegram_material_delivery_report.json \
  --delivery-log outputs/logs/telegram_material_delivery_log.jsonl \
  --send \
  --timeout 30
```

如果使用 Hermes 标准 home channel 配置，也可以写成：

```bash
TELEGRAM_HOME_CHANNEL=<target-chat-id> python job-hunt/scripts/send_telegram_material_package.py \
  --workspace job-hunt \
  --package outputs/logs/telegram_material_package.json \
  --report outputs/logs/telegram_material_delivery_report.json \
  --delivery-log outputs/logs/telegram_material_delivery_log.jsonl \
  --send \
  --timeout 30
```

补发成功的验收条件：

```text
status: passed
sent_count: 9
text_delivered: true
document_delivered_count: 8
missing_telegram_configuration: false
```

这个命令只发送 `telegram_material_package.json` 中列出的文件，不调用
`execute_approved_material_commands.py`，因此不会重新运行 Hermes/DeepSeek。

### 8.6 2026-05-17 `/job_generate 4` 事故复盘

实测现象：

- Telegram 立即回复 accepted，并显示使用 `deepseek/deepseek-v4-flash` 后台运行。
- `/status` 显示 Agent Running: No，因为真正工作在 detached job-hunt 子进程中，不在
  gateway agent turn 中。
- 用户几小时后没有收到材料；旧实现还可能只在本地日志里留下失败，不主动告知用户。

实际根因：

- Hermes/DeepSeek Layer2 已完成，`job-fit-scorer`、`resume-tailor`、
  `application-tracker`、`submission-review-gate` 都是 `hermes_executor_passed`。
- `telegram_material_package.json` 已渲染 8 个 DOCX/PDF。
- 失败点是 Telegram delivery：先前子进程缺少 `TELEGRAM_CHAT_ID`，并且旧脚本不认
  Hermes setup 写入的 `TELEGRAM_HOME_CHANNEL`；后续手工补发在 sandbox 网络里出现
  DNS 失败。

修复后要求：

- `/job_generate` 子进程会加载 `~/.hermes/.env`。
- 插件会从当前 Telegram session context 注入 `TELEGRAM_CHAT_ID`，避免 detached
  子进程失去 chat id；若没有 session chat id，则回退 `TELEGRAM_HOME_CHANNEL`。
- 后台 waiter 在非零退出时主动发 Telegram 错误摘要，不能静默失败。
- progress monitor 会发送关键阶段百分比，用户可感知当前处于 Layer1 handoff、
  Layer2 stage、package render 还是 delivery。
- 若执行报告可复用，重复同一 `/job_generate <id>` 不再重跑 DeepSeek。

### 9. 停止后台搜索

```text
/job_search_stop
```

期望返回：

```text
Job search stopped: background watcher disabled.
```

## 本地开发验证

聚焦测试：

```bash
cd /Users/huyaohua/PycharmProjects/hermes-agent-job-hunt
.venv/bin/python -m pytest \
  job-hunt/tests/test_job_search_runtime_controller.py \
  job-hunt/tests/test_batch_job_pipeline.py \
  job-hunt/tests/test_job_search_command_parser.py \
  job-hunt/tests/test_user_action_router.py \
  job-hunt/tests/test_telegram_notification_digest.py \
  job-hunt/tests/test_orchestrate_job_generate.py \
  job-hunt/tests/test_telegram_material_package.py \
  plugins/job-hunt/tests/test_job_hunt_plugin.py -q
```

材料生成桥接测试：

```bash
cd /Users/huyaohua/PycharmProjects/hermes-agent-job-hunt
.venv/bin/python -m pytest \
  job-hunt/tests/test_material_command_local_bridge.py \
  job-hunt/tests/test_material_command_fit_scorer_bridge.py \
  job-hunt/tests/test_material_command_resume_tailor_bridge.py \
  job-hunt/tests/test_material_command_application_tracker_bridge.py \
  job-hunt/tests/test_material_command_submission_review_gate_bridge.py -q
```

手动 controller 验证，避免真实发送：

```bash
cd /Users/huyaohua/PycharmProjects/hermes-agent-job-hunt/job-hunt
../.venv/bin/python scripts/control_job_search_runtime.py start --workspace . --dry-run --offline --interval-seconds 60
../.venv/bin/python scripts/control_job_search_runtime.py status --workspace .
../.venv/bin/python scripts/control_job_search_runtime.py stop --workspace .
```

手动单轮真实发送验证：

```bash
cd /Users/huyaohua/PycharmProjects/hermes-agent-job-hunt/job-hunt
set -a
source ~/.hermes/.env
set +a
../.venv/bin/python scripts/control_job_search_runtime.py run-now \
  --workspace . \
  --python ../.venv/bin/python \
  --allow-network \
  --send-telegram
```

## 故障排查

### `Active: yes` 但没有推送

检查：

```text
/job_search_status
```

如果 `Watcher alive: no`，查看：

```bash
tail -n 200 job-hunt/outputs/logs/job_search_watch_loop.log
```

然后重新启动：

```text
/job_search_stop
/job_search_start
```

### `Last status: failed`

查看：

```bash
cat job-hunt/outputs/logs/job_watch_cycle_report.json
cat job-hunt/outputs/logs/notification_delivery_report.json
```

常见原因：

- `TELEGRAM_CHAT_ID` 未配置。
- 网络抓取失败。
- 某个 public careers 页面结构变化。

### `/job_latest` 仍然 0

检查是否存在：

```bash
ls job-hunt/outputs/logs/job_ranking_gate_decision_last_nonempty.json
ls job-hunt/outputs/logs/telegram_action_alias_map_last_nonempty.json
```

如果不存在，说明还没有任何非空匹配轮次。先放入手动岗位快照，或检查
`data/job_sources.json`、`data/candidate_profile.json` 和
`outputs/logs/job_ranking_gate_report.md`。

当前 source registry 已扩展到 11 个来源：Wantedly 手动 inbox、PFN、NTT Labs、
Rakuten、Mercari、LY Corporation、CyberAgent、Cybozu、Sony、Woven by Toyota
以及通用 manual inbox。注意：`manual_snapshot` 的 `url` 必须是本地路径；如果写成
`https://...`，`fetch_job_sources.py` 会跳过并给出警告，避免假装抓取成功。

整页 public careers 快照只作为 `extract_public_careers_jobs.py` 的输入，不再直接
进入 `deduplicate_raw_jobs.py` 的岗位 ranking。若再次看到页面标题类结果，例如
`テーマを選ぶ｜...`，优先检查：

```bash
jq '{skipped_snapshot_count, aggregate_public_snapshot_count}' \
  job-hunt/outputs/logs/job_deduplication_report.json
jq '.ranked_candidates[].title' job-hunt/outputs/logs/job_ranking_gate_decision.json | head
```

### `/job_generate 1` 找不到岗位

检查：

```bash
cat job-hunt/outputs/logs/telegram_action_alias_map.json
cat job-hunt/outputs/logs/telegram_action_alias_map_last_nonempty.json
```

当前别名为空时，动作路由会自动使用 last non-empty alias map。若两个文件都没有
`aliases`，需要先产生一次非空 ranking。

### `/job_generate <id>` 只显示步骤，不显示材料

检查：

```bash
cat job-hunt/outputs/logs/job_generate_orchestration_report.json
cat job-hunt/outputs/logs/telegram_material_package.json
```

错误指纹：

- `use_local_executors: false`：当前只记录 slash 命令，不会生成材料。Telegram
  插件不应出现这种状态；CLI 手动调试时去掉 `--no-local-executors`。
- `pending_supervised_skill_execution`：某个材料阶段没有走本地 executor。检查
  `data/material_stage_executors.json` 中的 `candidate_scripts` 是否存在。
- `document_count: 0`：材料包没有找到履历书/职务経歴書文件。查看
  `<action_id>_material_command_execution_report.json` 的 stage 结果。
- `telegram_delivery_contract: send_docx_pdf_only` 之外的文件类型不应出现在
  `document_files` 中；如果看到 `.md`，说明上游材料包没有按新的交付契约渲染。
- `Delivery errors: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing`：本地材料已
  生成，但 Telegram 文件发送缺少配置。
- `pdf_delivery_note: No PDF files were found...`：PDF export 回退没有运行成功。
  先看 `outputs/logs/*_material_command_execution_report.json` 里 `export_resume_pdf`
  / `export_polished_pdf` 的状态，再检查 `outputs/resumes/*_pdf_export_manifest.json`。
- `missing_telegram_configuration: true`：gateway 进程没有加载 `~/.hermes/.env`。
  重启 `hermes gateway run --replace` 后再发 `/job_generate <id>`。

快速本地复现：

```bash
cd /Users/huyaohua/PycharmProjects/hermes-agent-job-hunt/job-hunt
../.venv/bin/python scripts/orchestrate_job_generate.py \
  --workspace . \
  --command "/job_generate 1"
```

手动真实发送复现：

```bash
cd /Users/huyaohua/PycharmProjects/hermes-agent-job-hunt/job-hunt
set -a
source ~/.hermes/.env
set +a
../.venv/bin/python scripts/orchestrate_job_generate.py \
  --workspace . \
  --command "/job_generate 1" \
  --send
```

手动强制重新调用 Hermes，而不是复用已有执行报告：

```bash
cd /Users/huyaohua/PycharmProjects/hermes-agent-job-hunt/job-hunt
../.venv/bin/python scripts/orchestrate_job_generate.py \
  --workspace . \
  --command "/job_generate 1" \
  --generation-backend hermes \
  --hermes-provider deepseek \
  --hermes-model deepseek-v4-flash \
  --force-regenerate
```

### `/job_generate <id>` 生成 DOCX 但没有 PDF

PDF 现在由 Layer2 的 `resume-tailor` 导出步骤生成，优先 LibreOffice，缺失时走
日文 CID fallback。缺 PDF 不应阻塞履歴書/職務経歴書 DOCX 交付；先检查：

```bash
ls job-hunt/outputs/resumes/*_resume_ja.docx
ls job-hunt/outputs/resumes/*_cv_ja.docx
```

如果 PDF 存在但打开是文字化け/乱码，检查 manifest：

```bash
jq '{converter, export_method, generated_files}' \
  job-hunt/outputs/resumes/<job_basename>_pdf_export_manifest.json
jq '{converter, export_method, generated_files}' \
  job-hunt/outputs/resumes/<job_basename>_polished_pdf_manifest.json
```

可接受的 `export_method` 是 `libreoffice` 或 `cid_japanese_fallback`。旧 manifest
若显示 `stdlib_fallback`，说明 PDF 是旧版 Helvetica/UTF-8 fallback 产物，日文会乱码；
用当前 Layer2 exporter 重跑：

```bash
python job-hunt/skills/resume-tailor/scripts/export_resume_pdfs.py \
  --workspace job-hunt --basename <job_basename>
python job-hunt/skills/resume-tailor/scripts/export_polished_resume_pdfs.py \
  --workspace job-hunt --basename <job_basename>
```

## 安全边界

- 不会自动提交申请。
- 不会上传招聘网站材料。
- 不会点击最终提交按钮。
- Telegram `/job_search_now` 会联网抓取，但 Telegram 发送仍是 dry-run；本地脚本
  直接调用时仍需显式 `--allow-network` 才联网。
- `/job_search_start` 是用户显式启动的后台真实推送入口；它会联网抓取并尝试发送
  Telegram，但仍只推送岗位 digest，不执行申请提交。
- 所有申请材料生成仍需要用户通过 `/job_generate <id>` 显式触发。
- `/job_generate <id>` 会生成并可发送材料包，但只发送给用户审阅；不会上传招聘站点、
  不会点击申请按钮、不允许自动提交。

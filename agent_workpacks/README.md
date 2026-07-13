# LLMforScheduler 多 Agent 工作包

本目录用于协调 AAAI 论文与实验工作，主题是“带独立验证器的工厂订单智能排产 Agent”。

本工作包不会自动启动任何 agent。用户会在新的对话窗口中手动启动指定 agent；启动时，应让该 agent 先阅读自己的目录和共享文件。

## Agent 列表

| Agent | 目录 | 职责 |
|---|---|---|
| 项目主管 | `project_manager_agent/` | 负责总体范围、优先级、跨 agent 协调、证据边界、git 管理和最终 claim 安全。 |
| 实验管理 | `experiment_manager_agent/` | 负责实验计划、实验跟踪、结果接收、结果分析和论文表格交付。 |
| 开发框架 | `dev_framework_agent/` | 负责新增实验框架、聚合脚本、复杂度/案例分析工具；LLM harness 只作为暂停的附录候选维护。 |
| 开发运行 | `dev_runner_agent/` | 负责用 tmux 运行实验、管理本任务进程/资源、收集并转交实验产物。 |
| 论文写手 | `paper_writer_agent/` | 负责按 AAAI 风格完成文章大纲和正文；数据只从实验管理 agent 接收。 |
| 复现质检 | `qa_repro_agent/` | 负责复现检查、结果一致性、split 泄漏、verifier 约束和论文 claim 审计。 |

## 共享文件

- `CURRENT_TASK.md`：当前总任务、资源和 deadline。
- `CONTEXT_MANIFEST.json`：代码、数据和结果的权威路径。
- `shared/DECISIONS.md`：已定决策。
- `shared/EXPERIMENT_REGISTRY.md`：实验登记表。
- `shared/ARTIFACTS.md`：实验和论文产物登记表。
- `shared/RISKS.md`：风险和缓解措施。

## 全局规则

- 保持 `Process_narration=false`。
- 保持代码库干净：不要留下 tmp 文件、死代码或不必要文件夹。
- smoke 测试产生的临时文件完成后要删除，除非它们是论文证据或复现必需产物。
- 新实验必须写入新目录或新文件，不得覆盖已有结果。
- 长时间任务必须用 tmux 托管，不使用 nohup。
- 只操作本任务相关的命令、进程、tmux session、GPU 和文件。
- 严禁关闭、修改或影响本机其它无关任务。
- 不得为了提高结果修改 verifier 语义或业务约束。
- 未经项目主管批准，不得修改 `docs/task.md` 的业务语义。
- LLM 输出只有能被解析并通过同一 verifier 检查时，才算有效结果；当前主线不依赖 LLM 结果。
- 论文写手只能使用实验管理 agent 交付的数字，不能直接从未验证日志中取最终结论。
- 涉及文件修改的任务完成后，执行该任务的 agent 必须在自己的任务分支提交；不得直接向 `main` 或集成分支提交。
- 禁止暂存或提交单个超过 50 MiB 的文件；不得用 Git LFS、压缩或拆分方式绕过此限制，除非项目主管获得用户的明确书面批准。

## 已冻结项目策略

- 主线：verifier-backed industrial heuristic scheduling engine，不做 LLM 直接生成完整分钟级排班的主方法叙事。
- Split：Train=2020-2023，Dev=2024H1，Test=2024H2-2025，OOD/recent=2025-only。
- 实验范围：H1 full-670 portfolio timed heuristic；H2 full-670 fixed dispatching rules；H3 full-670 chunked wavefront ablation；H4 CP-SAT stratified-50 120s/case；H5 complexity/difficulty analysis；H6 verifier case study；H7/H8 仅可选附录。
- 模型/GPU：默认不新增 GPU 训练或推理任务；若恢复 LLM/SFT，LoRA/SFT 用 RTXPRO6000 4 卡，推理可用 8 卡，A6000 每卡任务数为 RTXPRO6000 的一半。
- 证据准入：只有已登记 artifact、同一 verifier、同一 split/metrics schema 且 QA 通过的数字才能进入论文主表。
- 论文红线：不声称全局最优、完备不可行证明、工业 KPI 提升或 LLM 全面优于所有排产方法。

## 启动协议

1. 阅读 `CURRENT_TASK.md`、`CONTEXT_MANIFEST.json` 和本 `README.md`。
2. 阅读自己目录下的 `AGENT.md`、`STATE.json` 和 `HANDOFF.md`。
3. 阅读 `shared/DECISIONS.md`、`shared/EXPERIMENT_REGISTRY.md` 和 `shared/RISKS.md`。
4. 默认只更新自己目录下的 `STATE.json` 和 `HANDOFF.md`；只有职责明确归属时才更新共享文件。
5. 如果被阻塞，在自己的 `HANDOFF.md` 写清 blocker，并通知 `project_manager_agent`。

## Git 协作与提交协议

1. 项目主管为每项会修改文件的任务指定当前集成基线和唯一分支名，格式为 `agent/<agent-name>/<task-slug>`；任务 agent 从该基线新建分支，不在 `main`、共享集成分支或他人分支上直接修改。
2. 任务 agent 只暂存本任务文件。提交前必须检查 `git status --short`、`git diff --check`、`git diff --cached --check`，并确认暂存的新增或修改文件均不超过 50 MiB。
3. 任务 agent 完成修改、必要验证和提交后，在自己的 `HANDOFF.md` 报告分支名、提交哈希、变更文件、验证命令、产物路径及未解决风险；不要自行合并、rebase、force-push、改写历史或删除分支。
4. `project_manager_agent` 收到报告后检查提交内容、验证证据、artifact 登记和大文件限制；仅通过检查的任务分支才合并到当前集成分支。未通过时退回原 agent 修正并产生新提交。
5. 纯阅读、仅运行既有实验且不修改仓库文件的任务不要求创建提交；一旦写入代码、文档、登记表、状态或 handoff，即适用本协议。

# 决策记录

## D1. 论文定位

论文主线重新定为“带独立 verifier 的工业启发式排产引擎”，而不是“LLM scheduler”或“LLM 直接生成排班”。

原因：当前最强、最可审计的证据来自 full-670 deterministic heuristic portfolio、dispatching-rule baseline、chunked wavefront 消融、CP-SAT stratified-50 对照和独立 verifier。把 LLM 放入主比较会把评审注意力带到“LLM 是否会排产”，偏离本文真正贡献。

## D2. LLM 的职责

LLM 相关实验不进入论文主实验。E5 prompts 可保留为 appendix/motivation-only 预备产物；E6 SFT/LoRA 和 E7 direct generation 暂停，除非项目主管后续明确恢复。

如果论文需要说明“为什么不用 LLM 直接排产”，最多使用小规模 direct LLM generation 或 E5 tool-call parse rate 作为附录动机；不得把 LLM 输出作为最终排班或主方法竞争点。

## D3. Verifier 是验收边界

任何生成的排班只有通过现有 verifier，并且使用相同业务语义，才算有效。

不得为了提升结果弱化 verifier 检查。

## D4. 实验范围

主动实验轨道改为 H0-H8：

- H0：叙事、登记和论文 claim 重写，删除 LLM 主方法表述。
- H1：沿用 E0/E1 full-670 主方法复现，主表标签为 `portfolio timed heuristic`。
- H2：沿用 E2 full-670 固定 dispatching-rule baselines。
- H3：沿用 E3 full-670 chunked wavefront 消融。
- H4：沿用 E4 `CP-SAT stratified-50 baseline, 120s/case`。
- H5：新增规模/难度分桶分析，按 operation_count、total_work_minutes、machine_load_ratio、worker_day_count 汇总 verified ok、infeasible_proven、runtime p50/p90/p95/max。
- H6：新增 verifier case study，选择 2 个复杂可行 case、1 个库存抵扣/零任务 case、1 个容量下界 infeasible case。
- H7：可选 CP-SAT stratified-50 600s/case 附录。
- H8：可选 LLM appendix/motivation，不进入主方法比较。

不做 RL、GNN、670 单全量 exact CP-SAT、大规模合成数据扩展。外部 JSPLib/FJSPLib/Taillard/DMU benchmark 只作为相关工作或未来工作，除非能快速无损适配库存、人员可用、设备副本和交期验收语义。

## D5. 结果 claim 边界

可以写：

- verifier 通过的可行排班；
- 容量下界证明的不可行；
- 运行时间和任务规模；
- strategy/portfolio ablation；
- verifier-backed acceptance；
- CP-SAT stratified-50 的子集对照结果，且必须显式标注 50-case subset 和 120s/case。

没有新增证据时不能写：

- 全局最优；
- 完备不可行证明；
- 工业 KPI 提升；
- LLM 全面优于所有排产方法。
- LLM 是本文主排产器或主比较方法。

## D6. Split 和实验范围冻结

主 split 固定为：

- Train：2020-2023；
- Dev/validation：2024H1；
- Test：2024H2-2025；
- OOD/recent：2025-only，作为 test 内的额外评估标签。

CPU solver、dispatching baseline 和 chunked wavefront 消融优先跑 full 670。CP-SAT 主表只跑分层 50，120s/case；600s/case 只作为可选附录。E5/E6/E7 暂停主线；LLM direct generation 或 tool-agent 结果仅在需要动机附录时小规模使用。

## D7. 本地模型和 GPU 使用

默认不新增 GPU 训练或推理任务。若项目主管后续明确恢复 LLM/SFT 路线，默认使用本机 Qwen 系列模型；LoRA/SFT 使用 4 张 RTXPRO6000；推理可使用 8 卡，但 A6000 每卡分配任务数按 RTXPRO6000 的一半配置。

GPU 只用于 LLM 推理或 LoRA/SFT；solver、verifier、OR-Tools 主线主要使用 CPU。

## D8. 论文证据准入

论文主表只接收已登记 artifact 且通过 QA gate 的结果。旧结果目录可作为背景说明；若要进入主比较，必须在同一 split、同一 verifier、同一 metrics schema 下重新汇总或复现。

## D9. Git 权限集中于项目主管

所有 agent 可修改职责范围内文件，但 Git 暂存、提交、分支、合并、推送和历史管理只由 `project_manager_agent` 执行。其它 agent 不得执行 `git add`、`git commit`、`git switch`、`git merge`、`git rebase`、`git reset`、`git push` 或改写历史。

任务 agent 完成文件修改和验证后，在自己的 `HANDOFF.md` 报告变更文件、验证、artifact 和风险。项目主管检查 diff、测试/QA 证据、artifact 登记和 claim 边界后，统一选择并提交本任务改动。

提交硬限制：项目主管禁止暂存或提交单个超过 50 MiB 的文件；不得以 Git LFS、压缩或拆分方式规避。例外必须由项目主管取得用户的明确书面批准。

# paper_writer_agent Handoff

## 当前状态

2026-07-11 更新：论文主线改为 verifier-backed industrial heuristic scheduling engine。E5/E6/E7 不进入主实验；LLM 相关内容最多作为附录动机候选，当前不写主 claim。

## 初始大纲

1. Introduction
2. Related Work
3. Problem Formulation
4. Verifier-Backed Heuristic Scheduling Framework
5. Scheduling Engine
6. Verifier
7. Experimental Setup
8. Results
9. Case Study
10. Limitations
11. Conclusion

## 等待事项

- `experiments/aaai2026/h_series_heuristic_table_draft.md` 已通过 QA，可用于 H1-H4 正文结果。
- `experiment_manager_agent` 提供 H5 complexity/difficulty metrics。
- `experiment_manager_agent` 提供 H6 verifier case-study artifacts。
- 确认后的相关工作引用列表。
- 图表 artifact 路径。

## H-series 写作边界

- 主贡献写：工业排产启发式 portfolio、独立 verifier 验收边界、670 单实证与 strategy ablation/CP-SAT 子集对照。
- 主结果写 H1-H4：H1 portfolio timed heuristic、H2 fixed dispatching rules、H3 chunked wavefront ablation、H4 CP-SAT stratified-50 120s/case。
- H4 必须单独成节，不与 H1-H3 full-670 rows 按 case_count 等价比较。
- 不写 LLM scheduler、最小 LLM tool-agent 证据、LLM 全面优越或 direct LLM 主对照。
- Limitations 主动说明：不证明全局最优，不提供完备现实不可行证明，标准 JSSP/FJSP benchmark 不是主证据，LLM 不是本文主排产器。

## 2026-07-11 可开始写作范围

可以开始：

- 论文大纲重写。
- 方法部分：Verifier-Backed Heuristic Scheduling Framework、Scheduling Engine、Verifier。
- 实验设置：split、full-670、H1-H4 口径、QA gate、claim boundaries。
- H1-H4 结果表述，必须引用 QA-passed `experiments/aaai2026/h_series_heuristic_table_draft.md`。

继续等待：

- H5 complexity/difficulty metrics。
- H6 verifier case-study artifacts。

不得写：

- H5/H6 的具体结果数字。
- LLM 主方法、LLM 主比较或 LLM 全面优越。

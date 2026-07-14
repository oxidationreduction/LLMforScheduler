# paper_writer_agent Handoff

## 当前状态

2026-07-15 更新：已完成完整中文 AAAI 风格论文初稿：
`paper/aaai2026_chinese_draft.md`。初稿包含题目、摘要、关键词、引言、
仅含 `[待补引用]` 占位的相关工作、问题定义、Verifier-backed 框架、启发式
引擎、独立 verifier、实验设置、H1--H3 主表、独立 H4 表、H5 分桶表、H6
四案例表、局限性、结论和仅附录的 H7 表。七个“图 X（待绘制）”占位给出了
目的、建议视觉内容、数据/文件来源和图注，未生成图片。主张边界已保持：H4
与 H1--H3 full-670 隔离；H7 仅附录；不写全局最优、广泛不可行、工业 KPI 或
LLM 主方法/主比较。每张表均标明已 QA 通过的来源路径。

2026-07-15 更新：已起草并更新 AAAI `Experiments` 章节：
`experiments/aaai2026/aaai_experiments_section_draft.md`。H1-H3 保持
full-670，H4 单列为 `CP-SAT stratified-50 baseline, 120s/case`，不作等
case-count 比较。H5/H6 artifact QA gate 已 PASS，正文现引用可审计的
H5 670-case scale/difficulty 分析与 H6 四案例 verifier study；H5 保留
derived `machine_load_ratio` 和 `load_ratio` non-substitute 边界，H6 保留
complex-feasible、inventory zero-task 与 capacity lower-bound
`not_applicable` 边界。H7 仅加入 `CP-SAT stratified-50 baseline,
600s/case appendix` 段落，不进入主 claim，也不与 E4-120 或 full-670
直接等价比较。此更新不改变 H5/H6 artifact 的 registry 状态。

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
- H5/H6 的 artifact QA gate 已 PASS；只能使用已登记 artifact 中的已审计数字和 case-level evidence，不得自行扩展 claim。
- H5/H6 artifact registry 已同步为 `paper_ready`；只可使用已审计数字和 case-level evidence，不得自行扩展 claim。
- H7 只可作为 appendix-only 600s/case 段落，不进入主实验 claim，也不得与 E4-120 或 full-670 直接等价比较。
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

- H5/H6 artifact registry 的 paper-ready 状态同步（由其所有者负责，不在本次写作范围内）。

不得写：

- 超出已登记 H5/H6 artifact 的具体结果数字或 case-level evidence。
- LLM 主方法、LLM 主比较或 LLM 全面优越。

## 2026-07-15 Experiments Draft Handoff

- Draft: `experiments/aaai2026/aaai_experiments_section_draft.md`.
- Evidence used: paper-ready H1-H4 values from
  `experiments/aaai2026/h_series_heuristic_table_draft.md`.
- Preserved boundaries: H1-H3 are full-670 only; H4 is isolated as the
  CP-SAT stratified-50 baseline at 120s/case; no global-optimality, complete
  infeasibility, industrial-KPI, or LLM-main-comparison claim is written.
- H5/H6 QA-PASS writeback: H5 reports audited 670-case empirical-tertile
  summaries with derived `machine_load_ratio` and non-substitute `load_ratio`;
  H6 reports the audited four-case E1 verifier study without upgrading
  feasible, zero-task, or lower-bound evidence into broad claims.
- H7 is appendix-only: `CP-SAT stratified-50 baseline, 600s/case appendix`
  reports 50 cases, 44 verifier `ok`, 6 `infeasible_proven`, 0 unsolved, and
  0 verifier-invalid; it is not directly comparable to E4-120 or full-670.

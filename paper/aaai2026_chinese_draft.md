# 面向工业订单排产的验证器驱动多策略启发式调度

**英文题目暂定：** Verifier-Backed Portfolio Heuristic Scheduling for Industrial Orders

**作者信息：** [待补]

## 摘要

工业订单排产同时包含订单交期、工艺路线、成品库存、设备副本并发和人员可用日等硬约束。将这一问题直接交给语言模型生成分钟级排程，难以给出稳定、可审计的约束保证。本文提出一个验证器驱动的工业启发式排产框架。系统先将订单需求扣除成品库存，按照工艺先后关系展开为分钟级任务；随后由多策略启发式 portfolio 在人员和设备时间轴上构造候选排程；最后由独立的排后 verifier 对数量、工序顺序、交期、人员资格与可用性、每日 480 分钟工时、设备集合和设备并发进行验收。我们在 670 个真实订单级实例上评估该框架。主方法得到 576 个 verifier 通过的可行或零任务最优排程，94 个实例由当前模型下的容量下界判定为不可行，未出现未解实例或 verifier-invalid 排程。固定单一 dispatching rule 会留下 28 至 34 个未解实例；chunked wavefront 的 chunk size 会影响覆盖率，chunk 25 的聚合计数与主方法持平。我们还报告复杂度分桶分析、四个可追溯的 verifier 案例，以及仅作附录的 CP-SAT 50 实例结果。本文不声称全局最优或完备不可行证明，而是强调可复核的工业约束验收边界。

**关键词：** 工业排产；启发式调度；约束验证；组合优化；可审计人工智能

## 1. 引言

制造现场的订单级排产通常不是单一目标的标准作业车间问题。一个订单会同时给出产品需求和相对交期；每种产品包含有序工艺路线；已有成品库存可以抵扣需求；设备具有可并发副本；工人只在特定日期可用，并且每日总工作时间受限。任何一个候选排程只要违反工序先后、人员资格、设备并发或交期，都不能直接投入使用。

现有调度研究长期使用 dispatching rule、局部搜索和约束规划来应对这类组合决策 [待补引用：调度综述与 dispatching rule 文献]。其中，启发式方法适合快速构造可行解，约束规划适合对明确建模的子问题进行搜索 [待补引用：CP-SAT/约束规划文献]。近年来，语言模型也被用于规划和调度 [待补引用：LLM scheduling 文献]，但直接让模型生成完整分钟级排程会将语义解析、资源选择和硬约束保证混在同一输出中，难以形成可靠验收边界。

本文的立场是：在当前工业订单数据语义下，语言模型不应替代排程器生成最终日程；更稳妥的系统结构是由确定性调度引擎生成候选解，并由 verifier 独立执行验收。我们将候选生成和约束验收分离，使任意已接受的排程都能回溯到具体订单、solution 和 verifier artifact。

本文的贡献如下。

1. 提出一个 verifier-backed industrial heuristic scheduling engine：多策略 portfolio 负责分钟级候选构造，verifier 负责硬约束验收。
2. 给出面向库存抵扣、工艺顺序、设备并发和人员日历的订单级建模与验收语义，并将容量下界可证的不可行结果与“当前策略未找到解”明确区分。
3. 在 670 个订单实例上提供可追溯实证，包括单一规则消融、chunked wavefront 消融、复杂度分桶、案例级验收和 CP-SAT 子集附录。

> 图 1（待绘制）：验证器驱动排产框架总览。建议内容：左侧为订单、库存、工艺、设备和人员日历；中间为净需求展开与 portfolio heuristic；右侧为 verifier、accepted schedule、infeasible lower-bound 和 unresolved 三类输出。数据来源：第 3 至第 5 节方法定义。建议图注：`候选排程只有在 verifier 返回 ok 后才进入 accepted schedule 分支。`

## 2. 相关工作

### 2.1 工业启发式与优先规则

优先规则以交期、剩余路线工作量或资源负载等信息决定下一个任务，具有实现简单、在线决策快和易于组合的特点 [待补引用：dispatching rules survey]。本文将 `earliest_due`、`round_robin_product`、`largest_route_work` 和 `smallest_route_work` 作为固定规则消融，而不是将其包装为学习方法。多策略 portfolio 的作用是利用不同规则在不同订单结构上的互补性，以提高当前时间预算内的可行覆盖率。

### 2.2 约束规划与 CP-SAT

CP-SAT 能够表达离散资源、顺序、时间窗和逻辑约束，常被用于 job shop 及其扩展 [待补引用：OR-Tools CP-SAT 文档与调度文献]。本文保留 CP-SAT 作为受控子集 baseline，而非把它作为主方法。由于 CP-SAT 只在分层 50 实例子集上运行，本文不将它与 full-670 启发式结果按实例数等价比较。

### 2.3 语言模型与调度

语言模型可用于自然语言任务分解、工具选择和解释 [待补引用：LLM agents 与 LLM scheduling 文献]。但本项目的数据约束包含分钟级资源占用、设备副本和累计中间产物关系。本文不将 LLM direct generation、tool-agent 或 SFT/LoRA 作为主实验比较对象；这些轨道保持暂停，仅可在未来作为附录动机研究。

## 3. 问题定义

每个订单实例包含以下五类输入。

1. **当前订单信息**：每条需求含产品标识、需求量和相对交期日。
2. **产品工序**：每个产品的工序序号、工序名称、单件耗时、所需设备集合和可选操作人员集合。
3. **相关产品库存**：初始成品库存，用于抵扣订单需求。
4. **可使用设备信息**：设备名称及可用副本数。
5. **每日可使用人员列表**：工人到可工作日期集合的映射。

设产品 $p$ 的订单总需求为 $d_p$，初始成品库存为 $I_p$，则待排的净需求为：

$$
n_p = \max(d_p - I_p, 0).
$$

只有 $n_p>0$ 的产品进入排产。产品 $p$ 的每个单位沿工艺路线依次经过工序 $o=1,\ldots,O_p$。一个 task 指定日期、开始与结束分钟、工人、所占设备、产品、工序和数量。若某工序要求多个非空设备，则这些设备必须同时占用，而不是从中任选其一。

本工作采用如下硬约束。

- **需求与库存约束：** 最终工序完成量满足每个产品的净需求，并在每个交期前满足累计需求。
- **工序顺序约束：** 后续工序不能消费尚未由前序工序产出的中间产物。
- **人员约束：** task 所选工人必须在该工序的可选人员集合中，且在对应日期可用；同一工人同日任务不得重叠，总时长不得超过 480 分钟。
- **设备约束：** task 必须占用该工序要求的全部设备；同一设备同日的重叠占用不能超过其副本数。
- **时间约束：** 每个 task 的持续时间必须与单件工时和任务数量一致，且排程不超过交期要求。

> 图 2（待绘制）：订单到任务链的语义示意图。建议内容：展示库存先抵扣需求，随后一个产品单位依次通过工序 1、2、3；每个节点标注所需工人、设备和分钟数。数据来源：`docs/task.md` 的业务语义。建议图注：`多设备工序同时占用所有指定设备，后续工序只能在前序产物可用后开始。`

## 4. 验证器驱动的多策略启发式框架

### 4.1 预检查与输出状态

求解器首先检查输入 schema、未知设备、未知工人和缺失工艺路线。随后执行资源容量下界检查。若总工作量、设备容量或特定可选人员子集的能力已经不能满足订单期限，系统返回 `infeasible_proven`。这里的“证明”只针对当前模型中可计算的容量下界，不等同于现实工厂中的完备不可行证明。

当库存完全覆盖需求时，系统返回 `optimal` 且计划为空。该状态在本文仅表示零任务情形的平凡最优，不表示一般订单得到了全局最优排程。若容量下界未排除实例，但当前时间预算内未构造出可行解，系统返回 `no_solution_found` 或 `time_limit`，两者均不被写成数学不可行。

### 4.2 Portfolio 候选生成

主方法使用 timed portfolio heuristic。在每次策略尝试中，系统根据产品净需求和工艺路线构造单位任务或 chunked wavefront 单元，在人员与设备日历上寻找最早可行时间槽。portfolio 包含按交期、产品轮转、路线工作量和交错状态选择的策略；在规模较大且设备负载较高的实例上，系统优先尝试 chunked wavefront 变体。

固定规则消融只运行一个指定的 unit strategy。相反，主方法会在统一时间预算内依次尝试多种策略。该设计使“单一规则未解”与“portfolio 覆盖”具有清晰的实验含义，而不依赖训练数据或模型参数。

### 4.3 独立验收步骤

候选 solution 不是最终接受条件。verifier 重新读取订单与 solution，检查 task 结构、库存抵扣、任务数量、工序先后、人员资格和可用日、人员重叠、每日工作时间、设备集合、设备并发、任务时长和交期。只有 verifier 返回 `ok` 的 `feasible` 或零任务 `optimal` 结果计入 accepted schedule。

> 图 3（待绘制）：候选生成和 verifier 验收的执行轨迹。建议内容：给出一个实例的策略选择、候选 task 序列、verifier 检查项以及 `ok` 或错误列表的输出。数据来源：`solver/schedule_solver.py` 与 `solver/verify_schedule.py`。建议图注：`verifier 将候选生成与约束验收解耦，接受状态依赖验收结果而非求解器自报状态。`

## 5. 实验设置

### 5.1 数据与切分

实验使用 670 个订单级 JSON 实例。冻结的 split manifest 包含 473 个 train、64 个 dev 和 133 个 test 实例；2025-only 的 64 个近期实例属于 test 的 OOD/recent 评估组。本文的 H1 至 H3 都覆盖完整 670 实例，不将它们误写为仅 test-set 实验。

### 5.2 比较设置与度量

主方法为 `portfolio timed heuristic`。H2 使用固定单一 dispatching rule，H3 使用 chunked wavefront 的不同 chunk size。H4 是 CP-SAT 在分层 50 实例子集上的 120 秒每实例 baseline。H7 是同一 50 实例子集上的 600 秒每实例附录运行。

报告指标包括实例数、verifier `ok` 数、`infeasible_proven` 数、未解数、verifier-invalid 数和运行时间。对规模分析，还报告经验三分位内的 verifier 结果与运行时间分位数。所有主表数字都来自已通过 QA 的 artifact；所有表格均在表后标注其来源。

## 6. 实验结果

### 6.1 Full-670 启发式主结果与消融

表 1 给出 H1 至 H3 的 full-670 结果。主 portfolio 在 670 个实例上产生 576 个 verifier `ok` 的排程、94 个当前模型容量下界不可行结果，未出现未解或 verifier-invalid 输出。固定单一规则的最佳两个设置各有 28 个未解实例。chunk 25 恢复到与主方法相同的聚合计数，而较小 chunk 留下 4 或 2 个未解实例。

| 设置 | H ID | 实例数 | Verifier `ok` | `infeasible_proven` | 未解 | Verifier invalid | 总运行时间 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Portfolio timed heuristic | H1 | 670 | 576 | 94 | 0 | 0 | 167.628 s |
| Fixed `earliest_due` | H2 | 670 | 546 | 94 | 30 | 0 | 149.063 s |
| Fixed `round_robin_product` | H2 | 670 | 548 | 94 | 28 | 0 | 139.882 s |
| Fixed `largest_route_work` | H2 | 670 | 548 | 94 | 28 | 0 | 140.998 s |
| Fixed `smallest_route_work` | H2 | 670 | 542 | 94 | 34 | 0 | 147.854 s |
| Chunked wavefront, chunk 5 | H3 | 670 | 572 | 94 | 4 | 0 | 157.910 s |
| Chunked wavefront, chunk 10 | H3 | 670 | 574 | 94 | 2 | 0 | 160.155 s |
| Chunked wavefront, chunk 25 | H3 | 670 | 576 | 94 | 0 | 0 | 172.358 s |

**表 1 来源：** `experiments/aaai2026/h_series_heuristic_table_draft.md`、`metrics_e1_full670_repro.json`、`metrics_e2_dispatch_baselines_20260707_153730.json` 和 `metrics_e3_wavefront_ablation_20260707_153731.json`。表中运行时间是观测到的 run record，不构成算法加速 claim。

结果说明：H2 和 H3 证明的是当前策略组合对覆盖率的影响。它们不证明 H1 的排程全局最优，也不说明任何已接受方案在现实生产中必然优于其他未比较方法。

> 图 4（待绘制）：H1、H2 和 H3 的 accepted coverage 对比。建议内容：以 670 为统一分母的分组条形图，显示 verifier `ok`、`infeasible_proven` 和未解数量；H2 四条固定规则与 H3 三个 chunk 分别分组。数据来源：表 1 的 QA-passed metrics。建议图注：`固定规则和 chunk size 改变当前时间预算内的可行覆盖率；图中不表达全局最优或质量排序。`

### 6.2 CP-SAT 分层子集 baseline

表 2 单独报告 H4。该 baseline 在分层 50 实例子集上以 120 秒每实例运行，得到 44 个 verifier `ok`、6 个 `infeasible_proven`、0 个未解和 0 个 verifier-invalid。由于它的实例范围和时间预算与表 1 不同，不能按表中数量直接与 full-670 结果作等价比较。

| 设置 | H ID | 评估范围 | 每实例时限 | 实例数 | Verifier `ok` | `infeasible_proven` | 未解 | Verifier invalid |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| CP-SAT stratified-50 baseline | H4 | 670 父集合的分层 50 实例子集 | 120 s | 50 | 44 | 6 | 0 | 0 |

**表 2 来源：** `results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/metrics.json`。H4 仅是约束规划子集 baseline，不是本文主方法。

### 6.3 规模与难度分桶分析

H5 对 E1 full-670 结果按经验三分位分桶。`operation_count` 和 `machine_load_ratio` 按当前 solver 语义从 raw orders 派生；`total_work_minutes` 和 `worker_day_count` 是可用的 raw-order 统计。manifest 中的 `load_ratio` 是工人容量指标，明确不能替代 `machine_load_ratio`。

| 特征 | 来源 | 低 / 中 / 高实例数 | Verifier `ok`（低 / 中 / 高） | `infeasible_proven`（低 / 中 / 高） | 运行时间 p50，秒（低 / 中 / 高） |
| --- | --- | ---: | ---: | ---: | ---: |
| `operation_count` | derived | 223 / 223 / 224 | 223 / 223 / 130 | 0 / 0 / 94 | 0.032 / 0.095 / 0.203 |
| `total_work_minutes` | available | 223 / 223 / 224 | 223 / 223 / 130 | 0 / 0 / 94 | 0.034 / 0.088 / 0.155 |
| `machine_load_ratio` | derived | 223 / 223 / 224 | 223 / 223 / 130 | 0 / 0 / 94 | 0.040 / 0.086 / 0.116 |
| `worker_day_count` | available | 233 / 214 / 223 | 192 / 182 / 202 | 41 / 32 / 21 | 0.065 / 0.077 / 0.097 |

**表 3 来源：** `experiments/aaai2026/h5_complexity_difficulty_metrics.json` 与 `h5_complexity_difficulty_table_draft.md`。每个特征的三组 bucket 都覆盖完整 670 实例，且均为 0 未解、0 verifier-invalid。94 个当前模型 `infeasible_proven` 结果集中于高 operation count、高总工时和高 machine load tertile，这是描述性观察，不构成因果难度结论。

> 图 5（待绘制）：H5 复杂度分桶图。建议内容：四个小面板分别对应表 3 的四个特征；每个面板显示低、中、高 bucket 的 verifier `ok`、`infeasible_proven` 和 p50。数据来源：H5 metrics。建议图注：`operation_count 与 machine_load_ratio 是按当前 solver 语义派生，load_ratio 不作为 machine_load_ratio 的替代。`

## 7. Verifier 案例研究

H6 将四个案例锚定到 E1 full-670 summary 的 order、solution 和 verify 路径。两个复杂可行案例展示大规模 task 链在 verifier 下的验收记录；库存案例展示净需求为零时的空计划；容量案例展示没有 schedule 时 verifier `not_applicable` 的正确语义。

| 类别 | 案例 | 审计证据 | E1 状态与 verifier 边界 |
| --- | --- | --- | --- |
| 复杂可行 | `SO-2025-04-0022-2` | 最大 E1-feasible 总工时 46,138.88 分钟；solution 记录 7,046 个 scheduled operations；E1 summary/verifier 记录 6,947 个 merged tasks。 | `feasible`；verifier `ok` |
| 复杂可行 | `SO-2022-12-0019-2` | 最大 E1-feasible merged task count 9,129；solve time 15.010928976 秒；solution 记录 9,280 个 scheduled operations。 | `feasible`；verifier `ok` |
| 库存抵扣 / 零任务 | `SO-2024-10-0032-2` | 需求量 5、库存量 5；solution plan 为空；E1 summary 与 verifier task count 为 0。 | 当前模型 `optimal`；verifier `ok` |
| 容量下界不可行 | `SO-2025-05-0003-2` | CMM CONTURA 10/16/6 的当前模型容量下界为 `10701.610000 > 10080.000000`。 | `infeasible_proven`；verifier `not_applicable` |

**表 4 来源：** `experiments/aaai2026/h6_verifier_case_study_manifest.json` 与 `h6_verifier_case_study_draft.md`。`not_applicable` 表示没有产生 schedule 以供验收，既不是 verifier 通过，也不是 verifier 失败。

> 图 6（待绘制）：复杂可行案例的多资源甘特图。建议内容：选取 `SO-2025-04-0022-2` 的一个可读时间窗口，按工人和设备绘制 task 占用，并标注 verifier 检查的工序顺序与并发边界。数据来源：H6 所引 E1 solution 与 verify JSON。建议图注：`案例图用于说明已记录排程如何被验收，不表示全部实例的质量分布。`

## 8. 局限性与负责任使用

本文的结论具有明确边界。

- **非全局最优：** 除库存完全抵扣需求的零任务情形外，本文不提供全局最优性证书。
- **非完备不可行：** `infeasible_proven` 仅覆盖当前模型中容量下界可证明的一类情况；其他未找到解的实例不应被称为不可行。
- **数据与外部有效性：** 670 个订单实例是本文的主证据。标准 JSSP/FJSP benchmark 不包含本数据中库存、人员日历和设备副本等全部业务语义，故不作为主比较。
- **LLM 范围：** 本文不评估 LLM 作为主排程器的优越性。E5 至 E7 保持暂停，不能据此声称语言模型在本任务中无效或有效。
- **部署责任：** 实际应用仍需结合现场数据质量、设备维护、临时插单和人工审批。verifier 的作用是提供已建模约束的验收，不取代生产管理责任。

## 9. 结论

本文提出了一个面向工业订单排产的验证器驱动多策略启发式框架。该框架将候选排程构造与硬约束验收分离，并在 670 个订单实例上给出可追溯证据。实验显示，portfolio 与 chunked wavefront 的策略选择影响当前预算内的可行覆盖率；verifier 为已接受排程提供统一验收边界；复杂度分桶与案例研究补充了聚合数字的可解释性。本文的贡献不在于宣称全局最优，而在于建立从订单数据、候选排程到可审计验收结果的完整证据链。

## 附录 A. H7：CP-SAT 600 秒分层子集运行

H7 使用与 H4 相同的分层 50 实例 cohort，但每实例时间上限为 600 秒。该运行完整覆盖 50 个实例，得到 42 个 `feasible`、2 个零任务 `optimal`、6 个 `infeasible_proven`，即 44 个 verifier `ok`、0 个未解和 0 个 verifier-invalid。H7 仅用于说明更长 CP-SAT 时限下的同一子集记录，不能与 H4 的 120 秒记录或 full-670 启发式主表进行等时限、等范围比较。

| 设置 | 评估范围 | 每实例时限 | 实例数 | Verifier `ok` | `infeasible_proven` | 未解 | Verifier invalid | p50 / p95 / max 求解秒数 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| CP-SAT stratified-50 baseline, 600s/case appendix | 与 H4 相同的分层 50 实例 | 600 s | 50 | 44 | 6 | 0 | 0 | 2.320 / 19.339 / 38.931 |

**表 A1 来源：** `experiments/aaai2026/metrics_h7_cpsat_stratified50_tl600_20260715_013325.json`。H7 实际最大求解时间低于 600 秒，不应被解释为更长时限在其他实例或其他范围上没有作用。

> 图 A1（待绘制）：H4 与 H7 的同 cohort 时限记录。建议内容：并列显示 120 秒和 600 秒的 50 实例结果，突出相同 cohort、不同预算这一事实，并在图中明确标记“不可与 full-670 主表直接比较”。数据来源：E4 120s metrics 与 H7 600s metrics。建议图注：`图仅呈现同一分层子集在两种时限下的记录，不对不同时间预算作因果性能结论。`

## 参考文献占位

- [待补引用 1] 工业调度与 dispatching rule 综述。
- [待补引用 2] 约束规划与 OR-Tools CP-SAT 文档或论文。
- [待补引用 3] Job shop / flexible job shop benchmark 与建模文献。
- [待补引用 4] 语言模型工具调用、规划或调度相关工作。

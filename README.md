# TianjinLLM 排班求解器说明

## 项目概述

本项目使用基于求解器的方式进行任务排班：读取原始订单中的订单需求、产品工序、库存、设备数量和人员可用日，生成分钟级排班方案，并用 verifier 检查方案是否满足业务约束。

项目结构如下：

- `docs/`：任务说明和业务约束文档。
- `raw_orders/`：原始订单输入 JSON，当前全量数据共 670 条。
- `solver/`：排班求解器代码，核心入口是 `schedule_solver.py`。
- `solver/results/`：批量求解结果目录，包含每条 case 的 solution、verify 和 summary。
- `checker/`：排班验证程序，核心入口是 `check_schedule.py`。
- `analysis/case_study/`：抽样 case 的排班可视化 HTML，用于人工检查方案。
- `analysis/data_analysis/`：订单、工艺和资源数据分析脚本或中间结果。
- `old_code/`：历史 API 调用结果、prompt、旧版代码等归档内容。

## 求解器和 verifier 的思路

### 求解器

求解器输入是 `raw_orders/*.json`，主要字段包括：

- `当前订单信息`：产品名称、需求量和期限。
- `产品工序`：每个产品的工序顺序、耗时、所用设备和可选操作人员。
- `相关产品库存`：已有库存，用来抵消订单需求。
- `可使用设备信息`：设备名称和可用数量。
- `每日可使用人员列表`：每个工人在第几天可用。

求解器输出是 solution JSON，核心字段包括：

- `status`：`feasible`、`optimal`、`infeasible_proven` 等状态。
- `solver_method`、`strategy`、`solve_seconds`：求解方法、命中策略和耗时。
- `plan`：按天组织的排班任务，每个任务包含产品、工序、数量、开始/结束分钟、工人和占用设备。
- `summary`：任务数、使用天数等摘要信息。

当前求解器的主要思路：

1. 先用库存抵消需求，只对净需求排产。
2. 将订单拆成产品工序链，并保留同一件产品的工序前后依赖。
3. 用分钟级时间轴建模，每个工人每天最多 480 分钟，每台设备按设备数量拆成多个可并发副本。
4. 先做容量下界检查，例如总工时、设备总容量、人员时间窗容量；明显超出资源上限的 case 直接返回 `infeasible_proven`。
5. 对可排 case 使用多策略 timed greedy：按交期、产品路线工作量、工人负载、chunked wavefront 等策略尝试，把每道工序插入最早可行的工人和设备时间槽。
6. 代码中保留 CP-SAT fallback：当贪心策略找不到可行解且仍有时间预算时，可用 OR-Tools CP-SAT 继续尝试。

### verifier

Verifier 输入是原始订单 JSON 和对应 solution JSON；也可以输入一个结果目录批量检查。输出是 JSON 摘要，包含 `checker_status`、错误数量、机器并发错误数量、任务数和按 case 的错误明细。

Verifier 的验证思路：

1. 解析 solution 的 `plan`，检查任务结构、排班天数和时间字段是否合法。
2. 复算库存抵消后的需求，确认最终完成数量满足订单需求和交期。
3. 检查产品工序顺序，保证同一件产品的后续工序不早于前序工序完成。
4. 检查每个任务的工人是否在该工序可选人员中，且该工人在排班日可用。
5. 检查每个工人同一天内没有重叠任务，且单日工作时间不超过 480 分钟。
6. 检查任务占用设备是否和工序要求一致，并默认校验设备并发容量；同一设备同一天的重叠任务数不能超过设备数量。
7. 检查任务耗时和数量是否匹配工序定义。

## 求解结果

当前全量结果目录：

`solver/results/all_machine_capacity_dynamic_chunk25_20260626_tl120/`

本轮覆盖 `raw_orders/` 下 670 条原始订单，批量求解总耗时 195.741 秒。结果摘要如下：

- 总输入：670 条。
- 成功得到可行/最优排班：576 条，其中 `feasible` 560 条，`optimal` 16 条。
- verifier 验证通过：576 条有排班方案的 case 全部 `ok`。
- 容量下界证明不可行：94 条，状态为 `infeasible_proven`，因此没有生成可验证的排班方案，verify 记为 `not_applicable`。
- 未求解完成或无结论：0 条，`not_solved_cases` 为空。
- 当前结果中的 `solver_method` 均为 `timed_greedy`；CP-SAT fallback 保留在代码中，但本轮全量结果没有依赖它产出解。

## case_study

`analysis/case_study/` 下放了 4 个可视化 HTML，用于人工检查排班是否合理。HTML 是单个 solver 解的甘特图，不是 DSV4 对比图；任务块支持鼠标悬浮查看具体信息，包括时间范围、工人、机器、产品和工序。

- `simple_sample1.html`：`SO-2025-05-0006-2`，简单样本，60 个任务块。
- `simple_sampl2.html`：`SO-2023-07-0004-2`，简单样本，48 个任务块。
- `complex_sample1.html`：`SO-2024-12-0028-2`，复杂样本，520 个任务块。
- `complex_sample2.html`：`SO-2023-08-0011-2`，复杂样本，1328 个任务块。


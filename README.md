# TianjinLLM 排班求解器说明

## 项目概述

本项目使用基于求解器的方式进行任务排班：读取原始订单中的订单需求、产品工序、库存、设备数量和人员可用日，生成分钟级排班方案，并用 verifier 检查方案是否满足业务约束。

项目结构如下：

- `docs/`：任务说明和业务约束文档。
- `raw_orders/`：原始订单输入 JSON，当前全量数据共 670 条。
- `solver/`：排班求解器和后处理代码，核心入口是 `schedule_solver.py`，可视化入口是 `visualize_solution.py`。
- `results/raw_view/`：批量求解原始结果目录，包含每条 case 的 solution、verify 和 summary。
- `results/html_view/`：由 solution 后处理生成的 HTML 甘特图目录，批量结果目录下的 `index.html` 是人工校验入口页。
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

- `status`：求解状态。
  - `feasible`：已经找到满足当前约束的可行排班，但不保证是全局最优。
  - `optimal`：当前实现里主要表示库存已经完全抵消需求、无需排产的零任务 case；如果后续使用精确模型并证明最优，也可以用这个状态表达最优证书。
  - `infeasible_proven`：已经通过容量下界或精确模型证明不可行，例如设备总工时超过可用容量。
  - `no_solution_found`：在当前策略和时间预算内没有找到可行解，但不代表数学上一定不可行。
  - `time_limit`：达到时间限制后仍未得到可用结论。
  - `solver_unavailable`、`model_invalid`、`invalid_input`、`failed`：分别表示求解器依赖不可用、模型构造失败、输入格式非法或其他异常失败。
- `solver_method`：使用的求解入口。当前批量结果主要是 `timed_greedy`，即带时间预算的多策略贪心；代码中还保留 CP-SAT fallback。
- `strategy`：实际命中的策略参数。例如 `unit_strategy` 控制先排哪类工序/产品，`worker_strategy` 控制同一时间候选里如何选工人，`day_strategy` 控制排期方向。
- `solve_seconds`：单条 case 的求解耗时，单位是秒。
- `plan`：按天组织的排班任务。每个 `day` 下有若干 `tasks`，任务字段包括开始/结束分钟、工人、机器、产品、工序、工序序号、数量和耗时。
- `summary`：输入规模和粗略复杂度摘要，例如净需求产品数、净需求总件数、工序数、总工时、最大交期、工人数和可用人天数。

一个可解样例是 `SO-2025-05-0006-2`，对应结果文件：

`results/raw_view/all_machine_capacity_dynamic_chunk25_20260626_tl120/solutions/SO-2025-05-0006-2.solution.json`

该 case 的关键输出如下：

```json
{
  "case_id": "SO-2025-05-0006-2",
  "status": "feasible",
  "solver_method": "timed_greedy",
  "strategy": {
    "unit_strategy": "earliest_due",
    "worker_strategy": "least_used",
    "day_strategy": "forward"
  },
  "solve_seconds": 0.018801150959916413,
  "summary": {
    "product_count": 1,
    "net_required_total": 6,
    "step_count": 6,
    "total_work_minutes": 488.70000000000005,
    "max_due_day": 22,
    "worker_count": 12,
    "worker_day_count": 244,
    "complexity_score": 2088.7
  },
  "plan": [
    {
      "day": 1,
      "tasks": [
        {
          "start_minute": 0.0,
          "end_minute": 20.92,
          "worker": "张福仙",
          "machines": ["CMM CONTURA 10/16/6"],
          "machine": "CMM CONTURA 10/16/6",
          "material": "6521523",
          "process": "来料检",
          "step_index": 1,
          "quantity": 1,
          "unit_duration_minutes": 20.92,
          "duration_minutes": 20.92
        }
      ]
    }
  ]
}
```

这个例子里，`status=feasible` 表示已经找到可行排班；`timed_greedy` 表示由限时多策略贪心解出；`earliest_due + least_used + forward` 表示优先排交期更早的任务、优先选择当前负载较低的工人、从前往后排日期。`summary` 表示库存抵消后还需要生产 1 类产品共 6 件，每件有 6 道工序，总加工工时约 488.7 分钟，最晚交期是第 22 天。`plan` 中第一条任务表示第 1 天 0.00 到 20.92 分钟，由张福仙使用 `CMM CONTURA 10/16/6` 对产品 `6521523` 执行第 1 道工序 `来料检`，加工 1 件。

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

`results/raw_view/all_machine_capacity_dynamic_chunk25_20260626_tl120/`

对应的 HTML 可视化目录：

`results/html_view/all_machine_capacity_dynamic_chunk25_20260626_tl120/`

本轮覆盖 `raw_orders/` 下 670 条原始订单，批量求解总耗时 195.741 秒。结果摘要如下：

- 总输入：670 条。
- 成功得到可行/最优排班：576 条，其中 `feasible` 560 条，`optimal` 16 条。
- verifier 验证通过：576 条有排班方案的 case 全部 `ok`。
- 容量下界证明不可行：94 条，状态为 `infeasible_proven`，因此没有生成可验证的排班方案，verify 记为 `not_applicable`。
- 未求解完成或无结论：0 条，`not_solved_cases` 为空。
- 当前结果中的 `solver_method` 均为 `timed_greedy`；CP-SAT fallback 保留在代码中，但本轮全量结果没有依赖它产出解。
- 当前全量结果已转换为 670 个订单 HTML 文件，保存在 `results/html_view/all_machine_capacity_dynamic_chunk25_20260626_tl120/`；入口页是 `results/html_view/all_machine_capacity_dynamic_chunk25_20260626_tl120/index.html`。
- 入口页可以按订单搜索/筛选并打开对应排班页。单订单页顶部有简短说明，解释色块、视图和库存表的含义。
- 单订单页顶部先展示不随 Day 变化的求解摘要，例如 `Solution`、`Verify`、机器并发错误、总任务数、排程天数、求解方法和耗时。
- 单订单页支持按 Day 切换；Day 下拉框下方展示会随 Day 变化的当天摘要、工序产物库存、3 张甘特图和当天任务顺序表。3 张甘特图分别按工人检查人员占用，按机器检查设备占用，按产品实例/生产流检查当天工序顺序。
- 单订单页还展示订单需求、工艺路线、单件耗时、所需机器、可选工人等任务信息。
- 库存表按工序产物展示，而不是只展示最终产品：每道工序完成后形成一个流程产物，下一道工序会消耗上一道工序产物；最后一道工序产物视为成品库存。表中展示每个工序产物的 Day 开始库存、当天生成、当天被下一工序消耗、Day 结束库存；成品行额外展示订单需求、净需求和成品订单剩余。可行 case 展示具体排班，不可行 case 展示状态、输入摘要和不可行原因。

查看已经求解完成的排班结果时，先把仓库 clone 到本地：

```bash
git clone https://github.com/lxd99/LLMforScheduler.git
cd LLMforScheduler
```

然后直接双击或打开这个入口文件即可：

`results/html_view/all_machine_capacity_dynamic_chunk25_20260626_tl120/index.html`

注意不要只单独拷贝 `index.html`。这个入口页会按订单加载同目录下的 `SO-*.html` 文件，因此需要保留整个目录：

`results/html_view/all_machine_capacity_dynamic_chunk25_20260626_tl120/`

在 macOS 上也可以用命令打开：

```bash
open results/html_view/all_machine_capacity_dynamic_chunk25_20260626_tl120/index.html
```

如果浏览器安全策略导致订单页没有加载，再改用本地静态文件服务：

```bash
python3 -m http.server 8765 -d results/html_view/all_machine_capacity_dynamic_chunk25_20260626_tl120
```

然后在浏览器打开：

`http://127.0.0.1:8765/index.html`

## case_study

`analysis/case_study/` 下放了 4 个可视化 HTML，用于人工检查排班是否合理。HTML 是单个 solver 解的甘特图，不是 DSV4 对比图；任务块支持鼠标悬浮查看具体信息，包括时间范围、工人、机器、产品和工序。

- `simple_sample1.html`：`SO-2025-05-0006-2`，简单样本，60 个任务块。
- `simple_sampl2.html`：`SO-2023-07-0004-2`，简单样本，48 个任务块。
- `complex_sample1.html`：`SO-2024-12-0028-2`，复杂样本，520 个任务块。
- `complex_sample2.html`：`SO-2023-08-0011-2`，复杂样本，1328 个任务块。

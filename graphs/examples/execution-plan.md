# 巡检与缺陷双目标：Graph 执行文件

性质：绑定既有虚构案例的已填执行计划；本文件不是新增运行回执，当前状态 NOT_RUN。

| 项目 | 本次定义 |
| --- | --- |
| run_id / 入口 | demo-graph-evidence；[任务协调者](../../agents/task-coordinator.md)接受 Brain 目标后调取 Graph |
| 模板 / 定义 | [计划模板](../templates/execution-plan.md) / [实际 JSON](../evidence-goals.json) |
| 原目标 | 巡检覆盖 log-window、api-response、build-report；缺陷覆盖 tests、behavior、handoff |
| 环境与范围 | 本地 Python，独立虚构文件；无公司服务、模型、Java 构建或部署 |
| 并发与预算 | 既有案例 max_parallel=2，每场景总预算 20 秒；执行时绑定独立临时运行根 |
| 总体状态 | 当前 Graph；子 Loop 仅交局部回执 |

| 节点 | 依赖与责任 | 输出及门槛 |
| --- | --- | --- |
| inspection | 无依赖，已注册虚构巡检适配器 | 巡检 Loop 真实返回覆盖与缺证 |
| defect | 无依赖，已注册虚构缺陷适配器 | 缺陷 Loop 返回测试、行为与交接 |
| review-inspection / review-defect | 各自 Loop 完成后，确定性证据程序 | 重读当前产物和身份，不冒充独立模型审查 |
| close | 两个 Gate | 必需分支全部满足才整体完成 |

单轮阶段按[来源观察 Workflow](../../workflows/service-inspection.md)与[整体验收 Workflow](../../workflows/defect-completion.md)的职责合同解释。程序适配器执行虚构输入，不能声称已启动这些领域的真实 Agent。

责任 Agent 可运行 `python3 -B graphs/examples/goal-loops/run.py`；三个场景应分别保留 SUCCEEDED、PARTIAL 和 UNKNOWN 的预期结果，不将负例退出解释成业务完成。实际记录见[原案例](goal-loops/README.md)，本文件不复制其历史证据。

返回：[执行文件目录](README.md)。

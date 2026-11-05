**目的**：导航平级于 Standards 的执行工具与接口，并说明其能力和权限边界。

**适用于**：经 Skill 选择执行实现的责任 Agent 与维护者；不作为 Brain 直接调用入口。

# Tools：执行工具与共享代码

Tools 与 Standards 平级，共同作为 Skill 的基础资源。Standards 定义方法、规则与验收；Tools 提供可调用程序、执行适配器和控制器。Agent 经 Skill 适配工具，Brain 不直接调用 Tools。

| 用途 | 工具入口 | 当前边界 |
| --- | --- | --- |
| 统一案例入口 | [命令控制](workflow_entry.py)、[CLI合同](../docs/cli.md) | 五个白名单案例，固定输入检查点、未知不重放；不执行任意命令或拦截Brain身份 |
| 固定结构基准 | [评估工具](capability_benchmark.py) | 8个作者标注任务、同输入判定、原始计时及脚本还原；不证明工程收益 |
| 本地明确文件取证 | [本地适配器](local_evidence.py) | no-follow、逐文件 SHA、字节预算与集合覆盖；不扫描目录或判读取授权 |
| 反证报告结构检查 | [挑战工具](conclusion_challenge.py) | 核候选、矩阵、反证状态与敏感性覆盖；不验事实、理由或来源独立性，始终不作语义接受 |
| 显式页观察覆盖判定 | [覆盖工具](evidence_coverage.py) | 同查询/快照、游标、正控制、sample/complete及停止；不发起来源请求或证明真实权限 |
| 模块规划结构检查 | [模块计划工具](module_plan.py) | 对独立交入的设计合同核覆盖、写集、一致性边界和无环依赖；不确认设计正确、真实基线或实施授权 |
| 文档声明与档案字节检查 | [文档合同检查](document_contracts.py) | 只检查声明位置、覆盖清单与历史字节，不判定目的语义或授权 |
| 历史公开来源定位 | [历史来源工具](public_history.py) | 仅供旧回执核原公开版本；当前运行仍读取当前定义 |
| 工作区、沙箱、命令型并发与构建 | [执行工具](execution/README.md) | 按平台、工具与隔离模式分别准入，不支持任意工程 |
| Loop 决策与发现账本 | [判定](loop_policy.py)、[发现账本](finding_ledger.py) | 纯判定不自动执行模型或外部操作 |
| 巡检补证与缺陷收口 | [巡检控制](inspection_loop.py)、[缺陷控制](defect_loop.py) | 具体采集与业务行为依赖显式适配器 |
| 目标 Graph 的校验、运行与证据门禁 | [定义](goal_graph.py)、[运行器](goal_graph_run.py)、[证据核验](goal_graph_evidence.py) | 节点类型与 handler 必须满足合同，不执行任意输入代码 |
| 原生派工、研发链与恢复 | [原生适配](native_agents.py)、[执行链](native_flow.py)、[恢复](native_recovery.py) | 需要正常宿主能力和授权，不自动注册全局角色 |

[执行计划与工具适配 Skill](../skills/task-execution/SKILL.md)供责任 Agent 选择现有接口。工具内部组合其他工具是实现依赖，不新增框架层级；scripts 中的命令行入口是 Tools 的启动适配，也不另成一层。文档调用规则由助手/使用者遵循，现有 CLI 不验证调用者是不是 Brain 或 Agent。

返回：[项目入口](../README.md)。

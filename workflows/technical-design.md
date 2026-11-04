**目的**：组织方案编制、冻结专业审验、定向修订和设计交付，保留同候选证据。

**适用于**：有明确需求或技改目标的设计任务；无需 Graph/Loop 时单轮采用，未获权不实施工程。

# 技术方案 Workflow

由[任务协调者](../agents/task-coordinator.md)或入口专项 Agent 承接本轮目标，固定实际工程、候选、读写集和预算，先保存当前执行计划再执行受控动作。

| 阶段 | 责任 Agent | 输入与实际返回 | 失败去向 |
| --- | --- | --- | --- |
| D00 定界 | 协调者/方案作者 | 已决/未知、来源、范围与当前阶段 | 缺项只停依赖设计 |
| D10 编制 | [方案作者](../agents/design-author.md) | 需求到设计/验收与旧行为映射、契约、风险及恢复 | 来源/语义冲突回 D00 |
| D20 冻结与专业审验 | [设计复核者](../agents/design-reviewer.md) | 同一候选、真实上下文、覆盖与可定位发现 | 回原作者修相交项 |
| D30 定向修订 | 原作者与原审验者 | 新候选、失效项和对应复核 | 原预算到限保未决 |
| D40 保存与文档核验 | [文档维护者](../agents/document-maintainer.md)、[文档审查者](../agents/document-reviewer.md) | 实际落点、目的/适用与同候选内容结论 | 文档问题回原作者/维护者 |
| D50 交付 | [交付规划者](../agents/delivery-planner.md) | 专业、文档与实现状态分别报告，明确可继续范围 | 缺必要回执不报设计就绪 |

完整设计之后如需模块包，交[模块规划 Workflow](design-to-modules.md)。专业、文档、原则、用户接受和代码运行互不替代；分离审验无法取得则报作者自查/待审，不靠切换角色名称签独立通过。

[本轮计划模板](templates/technical-design.md) · [虚构贯通案例](examples/design-to-modules/README.md)

返回：[Workflows](README.md)。

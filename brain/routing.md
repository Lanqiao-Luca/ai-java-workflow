**目的**：按任务选择 Agent 或其上的组织入口，并保持阶段责任、授权和接续边界。

**适用于**：当前助手的新任务与续作；Graph、Loop、Workflow、Agent 均可作为路由入口，底层方法与工具经 Agent 使用。

# 职责路由：选择适用层级

## 先判断组织层

| 任务条件 | Brain 可选择的入口 | 采用边界 |
| --- | --- | --- |
| 多个目标存在依赖、并发或汇合要求 | [Graph](../graphs/README.md) | 选择覆盖当前目标的实际合同；Graph 组织 Loop/Workflow，不能把任意请求当可运行图 |
| 同一目标已有失败、发现或待补证，需要有限重复 | [Loop](../loops/README.md) | 核累计预算和停止条件，单轮由 Workflow 承载；无具体重复理由不启用 |
| 一轮任务需要多个阶段及角色交接 | [Workflow](../workflows/README.md) | 包含输入、写集、验收和实际责任，保持必要审验 |
| 专项解释、实现、诊断或审查，无需适用上层组织 | 下方对应 Agent | 由 Agent 选择 Skill，Skill 组合 Standards 与 Tools |

按 Graph→Loop→Workflow→Agent 判断适用性，只展开命中入口；它是从上向下的选择顺序，不是强制启用所有层。Brain 可选择组织模板和既有实例，实际运行由该层现有协调者、宿主和阶段职责承担。

## Agent 专项责任

| 当前任务 | 交给谁 | 接收后的职责 |
| --- | --- | --- |
| 选中组织入口的运行协调与接续 | [任务协调者](../agents/task-coordinator.md) | 协助维护已选实例、责任交接与总体状态；不作为进入上层组织能力的强制门槛 |
| 澄清目标、保持项与验收 | [需求负责人](../agents/requirement-analyst.md) | 确认契约和关键未知；不将建议当用户决定 |
| 已有流程分配的实现任务，或范围明确的单项改动 | [实现者](../agents/implementer.md) | 接受候选与写集，经 Skill 取得规则和工具 |
| 新增事实或核采集覆盖 | [证据采集者](../agents/evidence-collector.md) | 经 Skill 核来源、正控制和质量模式；多阶段任务可先选取证 Workflow，事实解释另交诊断 |
| 未知失败原因 | [诊断者](../agents/diagnostician.md) | 核合法证据与反证，缺事实不补猜测 |
| 行为验证、代码、语义或查询风险审查 | [验证者](../agents/verifier.md)、[代码审查者](../agents/code-reviewer.md)、[语义审查者](../agents/semantic-reviewer.md)、[查询审查者](../agents/query-reviewer.md) | 按问题选择专项责任，给定 SQL 审查不等于执行 SQL 或 DDL 获权 |
| 范围、目的、保留和完成声明 | [原则审查者](../agents/principle-reviewer.md) | 核同候选证据，不替代功能或业务验收 |
| 编制或修订技术方案 | [方案作者](../agents/design-author.md) | 经设计 Skill 核输入、当前能力、保持项与实质方案；需要多阶段组织时沿协调者进入 Workflow |
| 对冻结设计作专业复核 | [设计复核者](../agents/design-reviewer.md) | 经复核 Skill 核覆盖、反例与真实上下文，返回候选绑定发现 |
| 从当前设计形成模块包 | [模块规划者](../agents/module-planner.md) | 经规划 Skill 分配需求/写者与依赖，工具只核结构，实施准入另核 |
| 创建、更新本地文档或维护模板 | [文档维护者](../agents/document-maintainer.md) | 经文档维护 Skill 核目的、适用、原件和实际写入；多阶段任务沿原协调者组织 |
| 说明与实际能力一致 | [文档审查者](../agents/document-reviewer.md) | 核使用说明、来源和真实状态 |
| 只需交付顺序、残余与恢复计划 | [交付规划者](../agents/delivery-planner.md) | 规划，不代发布或部署；需要实际组织执行则交任务协调者 |

组织层由 Brain 根据任务选择；层内阶段责任由相应流程合同分配。当前协调者可以提供入口建议和运行支持，不要求所有任务先进入协调 Agent。已有实例和有效职责接续，不另派平行执行链。

## 续作与变化

- 普通继续：交原责任 Agent，复用有效状态和证据，不重建实例或重置预算。
- 验收、候选、环境或授权变化：由责任 Agent 判断相交阶段和失效范围，保留无关结果。
- 已受理操作结果未知：由当前责任 Agent 查状态，不换运行身份重放。
- 停止：通知当前责任 Agent 停止相关新动作，返回在途未知、最后可信状态和恢复条件，不预约后台继续。

缺必要角色或组织入口时列出具体缺口，只停依赖动作；Brain 不越过 Agent 直接执行 Skill、Standards 或 Tools。采用角色文档、原生安装和实际独立委派分别表述。

返回：[Brain 入口](README.md)。

# 交付规划者完整案例

把实现、验证、审查和发布分开，组织有依赖及恢复条件的真实计划。

全部材料独立虚构，仅复用仓库已公开的方法与示例；没有原私有框架、公司实现、凭证或真实业务记录。

## 一条链路怎样阅读

1. [任务与验收](case.json)：输入集合、输出集合、验收及运行边界。
2. [职责与方法消费](trace.md)：选择依据、逐步判断及反例。
3. 下方具体输入与分析产物：核结论能否回原材料，而非只看格式。
4. [结果与交接](result.md)：结论范围、未验和接续条件。

## 具体材料

- [inputs.json](inputs.json)
- [status.md](status.md)
- [plan.md](plan.md)

## 复制给AI

> 按 agents/delivery-planner.md 承担本次职责，先读 skills/delivery-planning/example.md 与本案例case.json。只读给定的独立虚构材料，经Skill选择Standards，交具体结论、证据、反例及未验。不要改业务源、连接服务、自动重试、注册平台或发布；示例里的拟动作不是本次执行授权。

## 状态与复核

这是作者手动采用角色合同形成的完整方法案例，未启动业务原生Agent。Java状态：not_applicable；数据库范围：not_connected。静态结构/身份检查只支持文件与引用状态，不支持业务运行。文件SHA由[案例身份清单](artifact-manifest.json)固定。

返回：[Skill案例入口](../../skills/delivery-planning/example.md)。

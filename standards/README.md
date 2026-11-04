**目的**：按任务导航原子规则和验收方法，保留正式入口与能力边界。

**适用于**：采用本仓库原子规则和验收方法的助手与维护者；实际调用须经责任 Agent 并核具体前提。

# Standards

独立维护方法和验收判据，与 [Tools](../tools/README.md) 平级，由 Skill 组合采用。按当前问题选择，不要求每轮全量加载。

- [设计输入与来源准入](design-inputs.md)
- [技术方案构造](technical-design.md)
- [设计专业复核](design-review.md)
- [设计到模块规划](module-planning.md)

- [文档目的与适用对象 PUR01/PUR02](document-purpose.md)
- [原子性质、范围与维护身份](atom-properties.md)
- [按需加载与导航](progressive-loading.md)
- [执行记录与跨窗口接续](execution-records.md)
- [上下文预算与执行单元](context-budget.md)
- [文档保留与原件保护](document-retention.md)

- [三层职责与方法合同](layering.md)
- [原则与证据边界](principles.md)
- [需求澄清与可观察验收](requirements.md)
- [实现基线与最小写集](implementation-baseline.md)
- [复用与旧行为保留](behavior-preservation.md)
- [共享规则与一致性](shared-rules.md)
- [Java/Spring 实现检查](java-spring.md)
- [风险驱动验证与完成声明](verification.md)
- [冻结输入、发现与定向复核](code-review.md)
- [需求到实现的语义核验](semantic-review.md)
- [证据驱动诊断](diagnosis.md)
- [SQL 与索引检查](sql-review.md)
- [异常恢复与有界尝试](recovery.md)
- [交付状态与接续规划](delivery-planning.md)
- [文档内容与引用验收](document-review.md)

- [执行实例的工作区与沙箱](workspace-isolation.md)
- [并发与候选合同](concurrent-execution.md)

- [可信Java构建沙箱](java-build-sandbox.md)：fork/loopback、离线缓存、子进程及失败/UNKNOWN合同。

- [Docker构建沙箱](docker-sandbox.md)：资源归属、命名空间/cgroup、输入输出、失败和UNKNOWN合同。

**目的**：并发组织容器构建 Workflow，并对合并候选执行双工具集成验收。

**适用于**：满足本地 Engine、受审镜像、工具和配额前提的公开 Spring 案例。

# Docker Spring Graph

用[Graph定义](docker-spring.json)并发调度两个真实构建，再合入精确提交进行双工具集成验收。

| 节点 | Workflow | 依赖/验收 |
| --- | --- | --- |
| title | [Maven标题](../workflows/docker-spring-title.json) | 无依赖；只改TitleApi，3项测试与Boot JAR |
| tags | [Gradle标签](../workflows/docker-spring-tags.json) | 无依赖；只改TagsApi，3项测试与Boot JAR |
| integration | [双工具集成](../workflows/docker-spring-integration.json) | 两者成功后精确合并，Maven/Gradle各8项测试与JAR |

同一Graph作业容量2；同宿主同运行根共享租约池。跨宿主是独立池，不提供分布式全局调度。内存/CPU/PID是每容器限制，不将2作业写成2个JVM。

每Graph/Workflow独立worktree及3个命名volume；Graph自己做探测，宿主可信调度器在容器外。每Workflow先探测容器再命令容器，完整案例共4实例、7容器、12卷；全部为本次唯一归属资源。无宿主bind/socket挂载，无外网，自己的loopback通信可用。

[完整案例](../examples/docker-spring-graph/README.md) · [Workflow合同](../workflows/docker-spring.md) · [先行计划](../docs/docker-sandbox-plan.md)

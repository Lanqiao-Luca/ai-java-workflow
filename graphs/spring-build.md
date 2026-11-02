# Spring Boot真实构建Graph

输入：冻结的独立虚构seed、[Graph JSON](spring-build.json)、显式JDK/Maven/Gradle、公开缓存种子、运行根与作业容量2。

| 节点 | Workflow | 依赖 | 输出 |
| --- | --- | --- | --- |
| title | [Maven标题构建](../workflows/spring-build-title.json) | 无 | TitleApi提交；3项真实测试；Boot JAR |
| tags | [Gradle标签构建](../workflows/spring-build-tags.json) | 无 | TagsApi提交；3项真实测试；Boot JAR |
| integration | [双工具合并验证](../workflows/spring-build-integration.json) | title、tags成功 | 两提交合入新实例；每种工具8项测试与Boot JAR |

共享2个Workflow槽位，内部子JVM不是另一个Graph槽位；Maven forkCount=1、Gradle max-workers=1。各实例拥有独立worktree、branch、策略、HOME/TMP及可写缓存/输出。进程树持续跟踪，Gradle一次性Daemon明确opt-in，须在客户端完成后3秒内停止；失败和未知不能提升。

[完整案例与重跑](../examples/spring-build-graph/README.md) · [构建Workflow合同](../workflows/spring-build.md) · [先行计划](../docs/spring-build-sandbox-plan.md)

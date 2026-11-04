**目的**：组织容器内功能变更、双工具构建与集成验收的单轮职责。

**适用于**：本地 Linux Docker Engine、受审镜像和明确写集内的公开 Spring 虚构案例。

# Docker Spring构建Workflow

消费[容器构建执行者](../agents/container-build-executor.md)的职责，经职责入口取得实现与隔离方法。调度由[Graph](../graphs/docker-spring.md)负责，Workflow不直接启动另一个Graph或模型。

沿用既有Spring Boot案例的Java/POM/Gradle/MockMvc业务输入，加入一份公开Mockito reflection MemberAccessor配置，避免Linux在禁用attach时反复尝试自附加。原始案例文件保持不变，新增覆盖文件单独列明来源/摘要，不能通过换名字复用公司业务数据。

命令仍为原build_task.py，写集仅TitleApi或TagsApi；集成不改源。复制的是无Git输入与各自可写缓存，不是宿主工作区挂载。完成后确认容器停止、JUnit/JAR与候选快照一致，再由宿主提升；合并后的两工具验收不可省略。

失败、超时、OOM/PID拒绝或不明结果不提升；后台残留失败，PID命名空间结束停止后代；不确定控制面状态保留原根、active和归属意图，不能换名字假定已恢复。

当前结果覆盖真实Spring测试与打包，未启动应用、接数据库或部署。平台须按实际控制器宿主标记，Linux guest与独立物理Linux不混淆。

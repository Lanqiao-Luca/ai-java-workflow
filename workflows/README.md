# Workflows

Workflow负责阶段顺序、输入输出交接和失败返回；各Agent自行选择Skill并消费Standards。研发流程合同可手动采用；新增JSON可由显式本地Graph执行器调度，不代表平台注册或原生LLM派工。

- [Java/Spring研发全流程](java-spring-development.md)：同一需求与候选，从澄清到实现、验证、审查、整改及交付。
- [完整虚构案例](../examples/workflow-bookmark-tags/README.md)：书签标签替换，真实Spring装配/MockMvc红绿测试与阶段证据。

## 实例并发执行

- [执行实例合同](concurrent-execution.md)：资源、前台沙箱、写集、状态和失败返回。
- [标题Workflow定义](concurrent-java-title.json)与[标签Workflow定义](concurrent-java-tags.json)：独立功能工作区，宿主派发前台JVM。
- [集成Workflow定义](concurrent-java-integration.json)：等待依赖，合并后重编译并运行8项断言。
- [Graph完整案例](../examples/concurrent-java-graph/README.md)：仅已测macOS前台后端，无fork型Maven/Gradle支持或原生LLM执行。

[执行文档](../docs/java-spring-workflow-plan.md) · [发布与验证结果](../docs/java-spring-workflow-results.md)

返回：[项目入口](../README.md)。

# 能力地图

按目标定位已有入口，不复制方法正文。角色通过自己的 Skill 取得 Standards；Brain 只选择组织与责任入口，不越过 Agent 调用方法。

| 目标 | 正式入口 | 验证来源与使用限制 |
| --- | --- | --- |
| 需求、实现、诊断或专项审查 | [Agent 目录](../agents/README.md) | [角色案例](../examples/README.md)分别保留实际状态，文档推演不作运行证明 |
| 一个业务变更走完研发链 | [Java/Spring Workflow](../workflows/java-spring-development.md) | [书签标签案例](../examples/workflow-bookmark-tags/README.md)记录 Spring 测试及同候选证据 |
| 原生上下文协作 | [原生 Graph](../graphs/native-java-spring.md) | [原生案例](../examples/native-spring-workflow/README.md)；需要当前宿主适配与正常模型访问 |
| 多任务并发构建 | [并发 Graph](../graphs/concurrent-java.md)、[构建 Graph](../graphs/spring-build.md)、[Docker Graph](../graphs/docker-spring.md) | [验证指南](../docs/validation-guide.md)列工具、平台和隔离限制，不默认任意工程兼容 |
| 有限重试、审查整改、巡检补证或缺陷收口 | [Loops](../loops/README.md) | [Loop 状态](../docs/loop-status.md)区分文档、离线控制与真实运行，预算不随恢复清零 |
| 多目标证据门禁与收口 | [目标 Graph](../graphs/goal-graph.md) | [Graph 状态](../docs/graph-status.md)与[虚构控制案例](../graphs/examples/goal-loops/README.md)；模拟业务证据不证明生产可用 |

使用前分别核对：定义是否适用、当前环境能否调用、当前授权是否覆盖、证据是否属于同一候选。入口缺失、未安装、调用失败和缺少许可分别报告；存在链接或配置不代表已经接通。

同任务复用已读且未变的来源。收到变更通知、来源不可读或上下文丢失时定向刷新，不承诺自动感知其他窗口变化，不扫描全部安装目录。

返回：[Brain 入口](README.md)。

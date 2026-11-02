# Loops

Loop 为同一任务提供有限重复与停止策略。具体单轮仍由 Workflow 组织，只有真实发现、技术失败或必要补证才选择重复；普通一次任务无需套用循环。

本批次按[执行文档](../docs/loops-extraction-plan.md)依次交付技术重试、审查整改与虚构案例。当前入口为方法目录，不是已安装的自动调度器。

[研发 Workflow](../workflows/java-spring-development.md) · [原生 Workflow](../workflows/native-java-spring.md) · [项目入口](../README.md)

- [技术失败的有界重试](technical-retry.md)：明确总尝试计数、未知结果查询与停止；附空表和可执行离线判定参考。

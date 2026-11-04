# Loops

Loop 为同一任务提供有限重复与停止策略。具体单轮仍由 Workflow 组织，只有真实发现、技术失败或必要补证才选择重复；普通一次任务无需套用循环。

本批次按[执行文档](../docs/loops-extraction-plan.md)依次交付技术重试、审查整改与虚构案例。当前入口为方法目录，不是已安装的自动调度器。

[研发 Workflow](../workflows/java-spring-development.md) · [原生 Workflow](../workflows/native-java-spring.md) · [项目入口](../README.md)

- [技术失败的有界重试](technical-retry.md)：明确总尝试计数、未知结果查询与停止；附空表和可执行离线判定参考。

- [审查整改的有界收敛](review-convergence.md)：同候选验收、发现复核、有限轮次及停止接续；附[完整虚构案例](examples/review-convergence.md)。

- [发现账本与证据失效](../docs/finding-ledger.md)：稳定发现 ID、作者修复与独立关闭分开，输入变化使旧证据失效；按[小步计划](../docs/loop-delivery-plan.md)验证与交付。

运行 `python3 -B scripts/check_loop_cases.py` 验证离线控制参考。正文与空表是方法，Python 是纯判定参考；[原生恢复控制器](../docs/native-recovery.md)现消费收敛判定，接入确认失败的有界整改与检查点续跑；纯判定函数本身不执行任何外部动作。

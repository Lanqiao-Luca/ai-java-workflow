**目的**：按任务导航同目标有限重复与停止，保留正式入口与能力边界。

**适用于**：采用本仓库同目标有限重复与停止的助手与维护者；实际调用须经责任 Agent 并核具体前提。

# Loops

## 模板与执行文件

- [templates：复用模板](templates/README.md)，由责任 Agent 填写为本次计划，不保存真实进度。
- [examples：执行文件与案例](examples/README.md)，包含已填计划及其实际运行或 NOT_RUN 状态。

Brain 可以直接选择并调取 Loop 作为任务入口，由本层合同组织下层职责，实际协调者、宿主和阶段 Agent 按真实执行方式承接。每层都可单独采用，无需强制启用更高层。方法合同由 Agent 手动组织，已有程序仅执行其支持的定义格式；填好 Markdown 模板不等于自动运行。

真实工程计划与进度存放于使用者授权的位置；examples 只放适合公开的执行文件和独立虚构案例。沿当前实例接续，不复制既有证据或用空目录冒充完成。具体合同见 [Loop 合同](review-convergence.md)。

Loop 为同一任务提供有限重复与停止策略。具体单轮仍由 Workflow 组织，只有真实发现、技术失败或必要补证才选择重复；普通一次任务无需套用循环。

[当前完成范围与待办](../docs/loop-status.md)区分已选交付、未迁入能力和真实运行未验项；上轮三项完成不代表六类 Loop 全部迁完。

本批次按[执行文档](../docs/loops-extraction-plan.md)依次交付技术重试、审查整改与虚构案例。当前入口为方法目录，不是已安装的自动调度器。

[研发 Workflow](../workflows/java-spring-development.md) · [原生 Workflow](../workflows/native-java-spring.md) · [项目入口](../README.md)

- [技术失败的有界重试](technical-retry.md)：明确总尝试计数、未知结果查询与停止；附空表和可执行离线判定参考。

- [审查整改的有界收敛](review-convergence.md)：同候选验收、发现复核、有限轮次及停止接续；附[完整虚构案例](examples/review-convergence.md)。

- [发现账本与证据失效](../docs/finding-ledger.md)：稳定发现 ID、作者修复与独立关闭分开，输入变化使旧证据失效；按[小步计划](../docs/loop-delivery-plan.md)验证与交付。

- [只读巡检的证据收敛](inspection-convergence.md)：按完整必查范围补证、保留异常与局部缺口；含[虚构日志/接口/构建案例](examples/inspection/README.md)。

- [缺陷的整体目标收敛](defect-convergence.md)：原验收、发现关闭、已受理操作和交接齐备才完成；含[测试通过仍未完成的虚构案例](examples/defect/README.md)。

运行 `python3 -B scripts/check_loop_cases.py` 验证离线控制参考。正文与空表是方法，Python 是纯判定参考；[原生恢复控制器](../docs/native-recovery.md)现消费收敛判定，接入确认失败的有界整改与检查点续跑；纯判定函数本身不执行任何外部动作。

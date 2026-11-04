**目的**：取得原缺陷目标的代码、行为与交接证据，避免单项通过代替整体完成。

**适用于**：已冻结完整验收与必要操作义务的缺陷任务；阶段动作须分别获权。

# 缺陷整体验收 Workflow

由[实现职责](../agents/implementer.md)处理获准的必要修复，[验证职责](../agents/verifier.md)返回候选绑定的测试与业务行为证据，[交付职责](../agents/delivery-planner.md)核必要制品、原操作回执、接收人及未决。代码审核仍沿[原生研发链](native-java-spring.md)，实际发现关闭复用其恢复控制器账本，不能由实现者自签。

执行前接原 goal_id、完整验收集合、当前候选/规则、原发现、已受理操作与剩余预算。已有有效证据复用，输入变化只从最早失效阶段继续；当前判据不得改成更容易通过的集合。测试回执来自实际宿主验证，行为/制品/交接回执必须能追至真实原件及 SHA；原始模型 JSON 不是可信执行回执。

单轮返回 context、finding_ledger、checks、operations、next_phase。每份 check 携 criterion_id、kind、context、status、evidence_id、artifact_sha256 和 observed_at；操作观察携稳定 operation_id、原 handle、真实 status 和回执 SHA。只有许可范围内的读证，不能因 Loop 请求缺证就新增业务写；需要修复或真实操作时由原授权执行者处理并保留预算与副作用记录。

结果交[缺陷 Loop](../loops/defect-convergence.md)判断总体完成。下一阶段可为 repair、verify、observe、handoff 或 none。未知受理先查原状态，不重新派发；调用失败或超时不标业务成功。控制器不自动提供真实业务连接器；虚构适配器只读取本地材料，模拟审核上下文并明确标注。

[Workflows](README.md)

# 发现账本与证据失效

[账本原语](../tools/finding_ledger.py)维护 OPEN → REPAIRED → CLOSED。原失败证据与事件始终保留；重复发现沿原 ID 追加观察。相同阶段/语义键不能换成另一个问题，身份与原判据不同则拒绝复用。

修复回执只证明作者提交了逐项修复声明。关闭必须同时取得验证、代码审查、原则审查的通过证据，三个执行上下文互相独立且不同于修复者，每份证据明确列出已复核的原发现 ID。泛化的阶段通过、作者自称修复、缺少某项复核均不能关闭发现。

全部正确性证据绑定当前候选、需求与规则的 SHA256。任一输入改变即将旧证据标 STALE，保留原状态和失效原因；依赖它关闭或修复的发现重开，不能换候选删除问题。没有输入变化则复用原有效证据，不为账本凭空增加一轮。

原语是纯数据合同：调用者负责提供真实执行/制品身份并持久化返回账本。它不执行模型、Git 或业务操作。[恢复控制器](../tools/native_recovery.py)现把阶段回执接入账本，以执行实例 ID 标识分离上下文，以实际输出 SHA 和宿主验证回执绑定证据。

验证、代码审查和原则审查分别输出 `verification-findings.json`、`code-review-findings.json`、`principle-review-findings.json`，字段为当前 `candidate_id`、已逐项复核的 `checked_findings`、剩余或新增 `findings`。每个发现保留稳定 `key`、`summary`、`location`、`criterion` 和原 `finding_id`（首次为 null）。同一原问题可由其他审查职责继续确认，不能改原判据。

实现者整改输出 `repair-actions.json`，携当前 `candidate_id` 和 `repaired_findings`。控制器只将所列问题标 REPAIRED，等待后续三项独立复核逐项确认。没有明确处理、没有逐 ID 复核、报告身份陈旧、报告与真实测试状态矛盾，均不能交付。`findings-ledger.json` 归控制器维护，角色不得修改。

控制器将账本同步到私有来源工作区和状态检查点；恢复不丢原发现与历史，需求/规则/源码变化均触发失效。新检查点合同为 recovery_version=2，旧版本/目录身份不匹配须停止，不自动重标旧回执。接线测试实际运行控制器及私有 Git worktree，角色/构建回执明确模拟；本批未重新运行真实模型整改链。

[收敛方法](../loops/review-convergence.md) · [回归测试](../tests/test_loop_findings.py) · [验证指南](validation-guide.md)

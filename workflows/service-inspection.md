# 只读来源观察 Workflow

目的：为一个已准入的必查项返回可核对的来源观察与身份，不以读取成功替代业务判断。

调用方交来源、对象/窗口、预期身份、读取许可和剩余预算。由[诊断职责](../agents/diagnostician.md)按已授权方法取得只读材料，[验证职责](../agents/verifier.md)核身份、新鲜度、完整性、原始内容摘要与覆盖边界。方法合同不自动启动 Agent，具体宿主须说明实际执行者。

返回 requirement_id、source、kind、完整 context、status、evidence_id、artifact_sha256、observed_at、finding 和 next_step。status 为 OBSERVED、MISSING、DENIED、UNKNOWN、FUTURE 或 CHANGE_REQUIRED；后四者不触发盲重试。MISSING 只有真实明确的新只读步骤才给 next_step。调用失败不能记作零条，HTTP503 等异常可作为已取得的观察，不声明健康。

读取适配器必须限制路径/对象、执行超时及内容大小，计算真实原件摘要，不扩大权限或把写入夹入补证。结果交[巡检 Loop](../loops/inspection-convergence.md)判断覆盖与继续，Workflow 不自行延长预算、轮询未来时点或调度后台任务。

虚构案例使用本地文件读取适配器执行本步骤，不派发模型 Agent、不连接公司来源。

[Workflows](README.md)

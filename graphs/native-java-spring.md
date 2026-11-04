# 原生Java/Spring Graph

[Graph定义](native-java-spring.json)读取六份[原生Workflow](../workflows/native-java-spring.md)。需求、实现和验证依次执行；两项审查从同一冻结基线并行，全部成功后交付。并发额度为2个Workflow作业，不等于总模型请求数或操作系统进程数。

每个节点都实际派发原生角色，具名单独的worktree、允许输出和上下文；父会话只能派工。不能用固定argv任务、角色扮演或父会话自己写代码冒充原生子Agent。

同批节点从同一base创建，写集相交时拒绝；任一节点失败时不提升本批产物、不启动后代，并等待已经运行的兄弟节点交回结果。未知状态保留，不自动清理、释放或重复有副作用的动作。

这是一组受限的可信虚构工程参考定义。原命令型Graph和Docker后端保持自己的运行边界，当前原生Graph不宣称把模型调用放进旧离线Docker环境。

[原生Graph引擎](../tools/native_flow.py)直接消费这组定义，使用[门禁测试](../tests/test_native_flow.py)核依赖、白名单提升、候选冻结与失败阻断。引擎测试中的角色明确为mock，虽然实际创建了虚构Git worktree，也不能算模型或Spring执行。[完整真实案例](../examples/native-spring-workflow/README.md)另有六个原生上下文、双审查调用重叠和25项离线Spring测试证据；不把两类结果混算。

可选择[恢复入口](../docs/native-recovery.md)，在失败证据确定且预算允许时交实现者整改，再重新验证与双审查；未知状态不重放。历史案例保持单轮实跑原义。

[接入计划](../docs/native-agent-workflow-plan.md) · [最小原生适配器](../docs/native-agent-adapter.md) · [Graph目录](README.md)

宿主许可前提：实测Codex 0.166会自动保存新执行目录的项目信任登记，必须获得明确平台写入授权。实例内角色配置不等于宿主零配置副作用；任务要求全局零写入时，当前原生后端应停止，不以其他身份或放宽沙箱替代。

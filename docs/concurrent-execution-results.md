# 实例隔离与并发Graph交付结果

本记录在主提交远程核验后填写，不写自身哈希。

- [先行执行文档050710f](https://github.com/Lanqiao-Luca/ai-java-workflow/commit/050710f939e538f4a4605796711eedfb7fc399df)：先保存、后实现。
- [机制与完整案例主提交8da7c53](https://github.com/Lanqiao-Luca/ai-java-workflow/commit/8da7c53554508e8833ec500da7409393bcf779b8)：新编写执行机制、方法与真实Graph案例。
- [执行文档](concurrent-execution-plan.md) · [Graph合同](../graphs/concurrent-java.md) · [完整案例](../examples/concurrent-java-graph/README.md)。

## 实际完成

每个run_id分配独立分支/worktree、实验Seatbelt策略、HOME/TMP及状态/证据；Graph按JSON引用3份Workflow JSON，宿主展开合同并执行前台argv。Agent/Skill文档参与catalog身份，不代表原生LLM自动调度。共享执行代码是机制实现，不是新方法层，不造空Loop。

| 检查 | 真实结果与范围 |
| --- | --- |
| 实例 | Graph自身与title/tags/integration共4实例，独立资源与父子归属 |
| 并发与依赖 | 2功能JVM时间区间重叠、峰值2；integration在二者成功后启动 |
| 合并与行为 | 两个精确提交均为集成输入祖先；合并后同JVM重新编译并执行8项断言，源HEAD未改变 |
| 内核权限 | 每实例10项探测通过：自身写、外部canary读写拒绝、Git管理canary读写拒绝、网络拒绝、外部硬链接创建/符号链接读取拒绝、fork/脱离会话派生拒绝 |
| 回收 | 干净停止worktree与可写HOME/TMP回收；失败脏/UNKNOWN保留及重复清理由专门回归覆盖 |
| 真实回归 | 26项、0失败、0错误、0跳过；临时虚构Git、自造canary及实际macOS内核后端 |
| 被动检查 | 公开清单/链接/方法交接、9角色+1Workflow+1Graph显式类型、源码/catalog、回执、所有案例SHA通过；不重跑业务命令 |
| 检查器负例 | 临时副本8项：合法例接受，未知类型/目录、核心或catalog漂移、probe失败、容量漂移、回归skip拒绝；不是额外Java实跑 |

真实回归与Graph回执绑定同一source_id：`9ed3248e443cf269f92f8a8652b9f384e4dc3ade1c5ebc1d281b8956bf8b23ad`。catalog_id：`136c24a23d0a72a83f794e7e42de99a6a2113a2cd0d994c7b57958317bdcdac7`，覆盖Graph、Workflow和参与Agent/Skill字节。详情见[运行回执](../examples/concurrent-java-graph/evidence/runtime.json)与[回归回执](../examples/concurrent-java-graph/evidence/tests.json)。发布侧复验身份与回执一致性，没有把相同源码重复测试冒充独立业务验收。

## 定向修复与技术收窄

独立复核的具体遗漏已关闭并追加回归：候选HEAD/index/代码漂移、宿主Git配置/过滤器入口、异常取消晚于等待、重复部分回收、fork/setsid后代控制及宿主SIGKILL后容量占用等。未公开原未修实现；最终包集合、案例集合与源码/catalog身份已闭合。

前台后端由内核默认deny fork，仅允许exec；JavaCompiler API在同JVM编译，不能承诺Maven/Gradle等fork型任务可直接运行。强杀宿主可能留下作业，持久active记录会quarantine同一运行根的池，不自动释放/换ID重用或杀旧PID；仅审计恢复，不自动续跑。

## 明确未覆盖

仅已测macOS已弃用sandbox-exec实验前台后端，无Linux/Windows裸进程回退。只支持ASCII相对路径，拒隐藏路径（含.gitignore/.github）、链接、子模块和属性过滤器；这份seed定义不适用于任意普通Java工程。允许必要系统metadata/根目录枚举和明确只读工具根，不是恶意多租户安全产品。

共享额度只覆盖同一runtime_root的本引擎实例，没有所有外部进程、总RAM/总磁盘或跨运行根的统一限制。有限canary不能证明所有逃逸不可能。本Graph未运行Spring、生产认证、数据库或部署；既有Spring13测试与角色教材历史状态保持独立，不改成并发Spring通过。

## 公开边界与核验

全部新增代码、数据与流程均独立构造，未读取原私有框架。工具二进制、运行根、原始日志、真实凭证和私有审计未进入Git。普通push到main，无force、Release、Actions、平台注册、后台服务或系统/全局配置修改。原有流程保留，相交目录与能力说明更新；远程ref与完整blob树在本次收尾后核对。

在列明范围与检查方法下，未发现未处理的公开问题；未验边界如上保留，不作完整安全或恶意代码绝对防护保证。

[首页](../README.md) · [案例目录](../examples/README.md)

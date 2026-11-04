**目的**：并发组织独立 Java 功能 Workflow，再合并同候选进行集成验收。

**适用于**：已测 macOS 严格前台沙箱及可信 Git 输入的公开纯 Java 案例。

# Graph调度多个Workflow

输入：可信Git仓库的明确提交、[Graph定义](concurrent-java.json)、宿主运行根、JDK只读路径及有限额度。

| 节点 | Workflow合同 | 依赖与输出 |
| --- | --- | --- |
| title | [标题功能](../workflows/concurrent-java-title.json) | 无依赖；生成/独立编译并检查TitlePolicy，产生提交 |
| tags | [标签功能](../workflows/concurrent-java-tags.json) | 无依赖；生成/独立编译并检查TagPolicy，产生提交 |
| integration | [集成验证](../workflows/concurrent-java-integration.json) | 等两项成功，在新worktree合入精确commit后重新编译并执行8项断言 |

Graph自身也分配worktree和sandbox并实际探测；调度期间不空占一个作业进程名额。所有Workflow使用同一max_parallel；采用同一运行根的其他Graph还共享宿主文件租约池。当前不支持递归Graph，不能在子任务自行另开进程逃过额度。

父子run_id、输入commit、输出commit、状态和证据均归各实例。各Graph状态由宿主单写；依赖失败仅阻断后代，独立分支可继续。集成冲突不擅自解决，也不修改源main。

仅受信任的本机任务，macOS实验前台后端；非平台自动AI调度。sandbox-exec已弃用，实际可用性每次探测；拒绝所有fork/派生会话。并发进程、墙钟/CPU和单文件大小有约束，不宣称总RAM/总磁盘或恶意多租户硬隔离。

[完整案例](../examples/concurrent-java-graph/README.md) · [Workflow说明](../workflows/concurrent-execution.md)

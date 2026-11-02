# 实跑结果

本案例使用独立编写的Java种子和临时虚构Git仓库。实际执行于macOS，Python 3与显式本地JDK 17，无公司服务、凭证、业务记录、私服或网络依赖。

| 检查 | 真实结果 |
| --- | --- |
| Graph与Workflow实例 | 4份独立worktree/branch、策略、HOME/TMP |
| 实际并发 | title与tags时间区间重叠；峰值2、Graph及共享池容量均为2 |
| 依赖与集成 | integration等待两者成功；两个精确提交均为合并后祖先；重新编译并通过8项断言 |
| 隔离探测 | 每实例10项通过：自身写、外部读/写、Git管理canary读/写、网络、硬链接创建、符号链接读、普通fork及脱离会话派生拒绝 |
| 来源与提升 | 源HEAD未变；源码/合同SHA绑定；候选HEAD/index/字节与写集复查后才提交 |
| 回收 | 4份干净worktree及可写HOME/TMP移除；演示临时夹具清理 |
| 回归 | 26项通过，0失败、0错误、0跳过；真实临时Git及内核沙箱 |

[运行回执](evidence/runtime.json)记录精确源码source_id、Graph/Workflow/Agent/Skill目录catalog_id及虚构提交身份。[回归回执](evidence/tests.json)记录实际测试名并绑定相同源码身份。[案例清单](artifact-manifest.json)核对本案例文件字节。

回归覆盖并发1/跨Graph共享容量、失败后代阻断与独立继续、冲突、超时、取消、成功证据缺失、写集/HEAD/index/字节漂移、脏资源保留、重复清理、宿主异常提前取消、被强杀宿主遗留容量隔离、UNKNOWN仅审计不重放，以及Git过滤器/配置漂移在宿主Git内容操作前拒绝。

## 范围

当前后端是已弃用的macOS sandbox-exec实验实现，只支持前台单进程（线程可用），禁止fork；Maven/Gradle派生任务暂不支持。源文件名只接受ASCII相对路径并拒绝所有隐藏路径（含.gitignore/.github）、符号链接、子模块、属性过滤器；该seed定义不能直接套任意Java工程。

墙钟、CPU、单文件大小和共享池配额不等于总RAM/总磁盘或跨运行根的全机器限制。允许必要系统metadata和根目录枚举、明确工具根只读。强杀宿主不保证自动杀尽作业；遗留active租约隔离池，需人工核实外部状态，不自动释放或向旧PID发信号。不能据有限canary证明所有逃逸不可能。

未运行原生AI Agent调度、Spring装配、生产数据库、部署或跨平台后端；此确定性宿主执行器不是LLM自动研发系统。既有Spring案例独立保留其13项验证结果，本次不冒用为并发Spring验证。

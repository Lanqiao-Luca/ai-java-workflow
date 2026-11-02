# 完整案例：Graph并发调度Java Workflow

独立虚构的两个需求：书签标题规范化与标签规范化。Graph实际并发两个功能Workflow，各自生成/编译/检查Java组件并产生提交；集成Workflow等待两者成功，合入精确commit，再重新编译并运行8项断言。

此案例不使用公司数据、真实账号、接口、数据库或日志；没有LLM/平台注册或外部服务调用。它验证本地并发执行机制，未运行Spring装配或生产部署；原Spring案例保留其独立13项实跑证据。

## 资源和交接

Graph自身与3个Workflow共4个实例，各有worktree、branch、sandbox策略、HOME/TMP。source base commit保持不变，父子ID和候选提交可核；title/tags实际时间区间须重叠，integration必须在两者完成后启动。

| 入口 | 内容 |
| --- | --- |
| [Graph合同](../../graphs/concurrent-java.md)与[定义](../../graphs/concurrent-java.json) | 依赖、全Graph额度及具体Workflow引用 |
| [Workflow执行合同](../../workflows/concurrent-execution.md) | 只支持前台进程，状态/写集/证据/失败返回 |
| [需求与过程](trace.md) | 输入、独立范围、资源、合并与验收 |
| [种子功能执行器](seed/FeatureWriter.java) | JavaCompiler API在同一JVM生成并验证功能 |
| [集成执行器](seed/Integration.java)与[8断言](seed/GraphAssertions.java) | 合并候选重新编译/验证，不复用分支绿灯冒充集成通过 |
| [实跑回执](evidence/runtime.json)与[结果](result.md) | 来源ID、隔离负例、真实并发/依赖与回收 |

## 重跑

需要macOS上可用sandbox-exec、Python3.9+、Git及显式本地JDK17+。该Apple工具已弃用，平台缺失/探测失败会拒绝，绝不降级为裸subprocess。

从项目根运行：

```sh
python3 -B examples/concurrent-java-graph/run.py --java-home <JDK目录>
```

可用`--output <案例之外的新文件>`保存脱离机器路径的摘要。运行器只造系统临时虚构仓库与canary，不读真实凭证，不改源码仓库main、不push、不下载依赖。所有构建类文件进入各自TMP；默认演示结束后删除自己的临时夹具。

真实业务仓库可显式用`scripts/run_graph.py --definition graphs/concurrent-java.json --repo <授权干净仓库> --base <明确提交> --runtime-root <仓库外专用目录> --run-id <唯一ID> --java-home <JDK目录>`；此特定定义要求同样seed合同，不能直接用于任意工程。所有Graph使用同一runtime_root才能共享宿主容量。`--cleanup`只回收干净停止资源；取消用`--cancel <实例目录>`，审计恢复用`--inspect <实例目录>`，不会自动重放未知任务。

## 限制

仅已验证的macOS前台后端；fork、后台任务和分离会话均由内核禁止。Maven/Gradle等需要子进程的命令暂不支持，应拒绝而不是绕过。CPU/单文件与进程额度不等于总内存/总磁盘或恶意多租户隔离。宿主被强杀时不保证自动杀尽作业，未知active租约会隔离池，需人工核外部状态；不自动释放或改旧PID。

宿主允许必要文件metadata、根目录枚举和明确只读工具根；不能宣称宿主所有信息不可见。源快照仅接受ASCII相对路径，并拒绝隐藏路径（含`.gitignore`、`.github`）；输入源及输出符号链接/子模块/属性过滤器不支持。自造canary负例只证明实际测试覆盖，不证明不存在所有逃逸可能。

返回：[案例目录](../README.md)。

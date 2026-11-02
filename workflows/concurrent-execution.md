# 受限前台Workflow执行合同

Workflow接受Graph分配的冻结输入和实例资源，消费现有[实现者职责](../agents/implementer.md)。角色通过工作区隔离Skill选择规范及宿主实现；本执行器只跑审核过的命令，不调用模型或伪造Agent回执。

每份JSON声明agent、skills、argv、逻辑写集、精确成功行和0.1–600秒预算。Graph先核DAG、来源和实际沙箱，再派发。当前命令只支持单前台进程，禁止fork；编译/检查示例使用JavaCompiler同JVM执行，不支持直接搬入需派生子进程的Maven/Gradle工作流。

作业可读自身工作区和明确工具根，只可写自身worktree及HOME/TMP；共享Git由宿主处理，网络默认拒绝。逻辑写集在提升前检查，超出范围保留工作区并失败，不提交。校验后的字节、HEAD或暂存区漂移也失败。

成功须退出0且输出声明的精确整行，success_pattern只支持`^字面文本$`，不是通用正则；这不代调用者对业务断言含义的判断。依赖输出合入新实例后必须运行该实例的独立验收。

取消、超时和协调者异常先停止已知进程，再释放已确认安全的租约。宿主SIGKILL留下的持久active租约不自动重用，池进入quarantine，inspect只标UNKNOWN和保留证据，不自动续跑、不杀旧PID。需可信人工核实外部状态后另作处置。

回收可重复执行；已安全删除的资源不再访问，脏/漂移/未知资源保留。保留私有状态、策略和必要证据，回收干净worktree及可写HOME/TMP；输出提交分支仍保留，未自动合入源main或push。

[Graph入口](../graphs/concurrent-java.md) · [Java/Spring方法Workflow](java-spring-development.md)

# 原生链路的有界整改、续跑与 CI

当前入口是[恢复运行器](../scripts/run_native_workflow.py)，组织既有[六阶段 Graph](../graphs/native-java-spring.md)，由[恢复控制器](../tools/native_recovery.py)消费原生引擎与 Loops 收敛判定。默认最多三轮（包含初轮），总预算 3600 秒；最多可选五轮、14400 秒。只有独立虚构示例进入此入口。

## 自动整改

真实子 Agent 的完成事件、结构化状态、声明输出、写集及文件身份一起核对。确认的验证或审查失败才进入整改；验证失败还必须取得同候选宿主构建回执。编译/测试非零退出可整改，超时、协议异常、缺输出、越权、身份漂移和未知副作用停止。实现、需求或交付失败保留断点，不擅自推定可修复。

失败文档及独立测试保留在私有运行目录。实现者的整改写集只包含已声明的生产源码和实现说明，POM、固定验收、作者测试与独立测试全部冻结。整改后重新独立验证，双审查从新冻结候选并行执行，最后交付。先前通过的审查不能覆盖新候选。相同或循环候选、轮数/时间到限均停止，不能靠续跑重置预算。

技术故障若缺少确定的完成与副作用证据，保持 UNKNOWN。控制器不自动重放远端模型调用、提交、推送或部署；这里的“自动续跑”指确认失败经整改后继续后续阶段，以及从安全暂停检查点恢复。

## 启动与续跑

需要 POSIX、Git、Python 3.9+、明确选择的 JDK 17/Maven、支持原生派工协议的 Codex CLI 与正常本机登录。沿用[原生适配器](native-agent-adapter.md)的可信工程、网络与沙箱边界。

```sh
python3 -B scripts/run_native_workflow.py \
  --run-root <仓库外的新私有运行目录> \
  --java-home <JDK目录> --maven-home <Maven目录> \
  --public-synthetic-input --allow-host-trust-registration \
  --max-rounds 3 --budget-seconds 3600
```

`--allow-host-trust-registration` 明确确认 Codex 宿主可能保存本任务执行目录的信任登记；本工具不改全局角色注册，不代替使用者选择登记保留/还原方式，也不清理其他配置。没有这项许可不能调用原生模型。原任务的临时登记收尾仍须核原回执，本次实现不推定它已完成。

可用 `--pause-after implementation` 或 `--pause-after verification` 在已提升的安全边界暂停（退出 3）。继续使用相同参数及同一个 `--run-root`，删除 `--pause-after` 并加 `--resume`。成功退出 0，失败/预算耗尽退出 1，准入拒绝退出 2。预算包含暂停时间。

恢复时核对原目录的种子、公开目录身份、Graph、预算、工具配置、源码快照与私有 Git HEAD。控制器持有单写者锁，每次准备与派工前持久化新尝试编号。RUNNING/UNKNOWN 状态不能自动恢复；进程崩溃即使没有产生业务文件也不意味着远端子任务已停止。只有 READY、PAUSED 检查点可以继续；已完成结果可读回，不重复执行。记录限可信本地所有者使用，不提供对恶意篡改检查点的认证保证。

每次尝试都有独立 worktree、原生上下文和私有日志。`state.json` 保存累计轮数、绝对截止时间、阶段历史、候选、输出摘要及检查点。失败原件不会覆盖成成功；这些文件可能含本机路径和会话信息，不能直接上传。

## 持续验证

[GitHub Actions](../.github/workflows/ci.yml)在 push、pull_request 和手动触发时运行，只授予 contents:read，不配置模型凭证、不触发发布。两类任务分别核证：

- Ubuntu/macOS、Python 3.9/3.12：八项离线检查及[便携回归套件](../scripts/check_ci.py)，覆盖原生协议、候选门禁、恢复/续跑、检查编排和 Docker 解析策略。使用明确模拟的原生角色与构建回执，不声称模型实跑或容器内核验证。
- Ubuntu、JDK 17：通过[Spring 冒烟入口](../scripts/check_spring_smoke.py)构建公开冻结候选，实际执行 Spring context/MockMvc 测试，从公开 Maven Central 获取依赖。它验证现有业务候选与构建器，不调用模型生成新代码。

本地对应命令：

```sh
python3 -B scripts/check_all.py
python3 -B scripts/check_ci.py
python3 -B scripts/check_spring_smoke.py --java-home <JDK目录> --maven-home <Maven目录>
```

恢复回归真实创建私有 Git/worktree并执行控制器，原生模型与构建结果使用模拟输入。历史六个原生 Agent、25 项 Spring 实跑仍保留[当时执行源码原件](native-baseline/README.md)；本轮未把其回执改成新恢复控制器的实跑证明。CI 首次远程执行的结果以实际 Actions 回执为准。

[验证指南](validation-guide.md) · [项目入口](../README.md)

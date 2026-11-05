**目的**：说明统一案例命令的输入、状态、检查点和边界，使每次运行可核对和安全接续。

**适用于**：Python3.9+、POSIX 上采用受信公开案例的责任 Agent；不是任意工程调度器或 Brain 调用身份拦截。

# 统一入口

[任务协调者](../agents/task-coordinator.md)经执行 Skill 采用 `python3 -B scripts/workflow.py`。目前白名单为 local-evidence、conclusion-challenge、module-plan、spring-archive、capability-benchmark；它们分别复用原案例函数，不能传任意 shell、加载任意插件或把 Markdown 自动编译为可执行流程。

```sh
python3 -B scripts/workflow.py doctor
python3 -B scripts/workflow.py choose --goal challenge
python3 -B scripts/workflow.py run --request workflows/examples/cli/challenge.json --run-root <仓库外全新绝对目录> --pause-after-preflight
python3 -B scripts/workflow.py status --run-root <同一目录>
python3 -B scripts/workflow.py resume --request workflows/examples/cli/challenge.json --run-root <同一目录>
```

choose 只按显式目标 collect/challenge/plan/spring/benchmark 映射方法入口，不是读取 Brain Markdown 的自动推理器。Brain 可先选组织层/Agent，责任 Agent 经 Skill 再适配这个工具。

## 输入与状态

请求为 `{"job":"conclusion-challenge","options":{}}`。除 Spring 外的案例 options 必须空；只操作原公开案例。spring-archive 必须显式传 java_home、maven_home、repository 三个绝对路径以及 offline 布尔值，repository 在仓库外；offline=false 明确允许公开 Central 依赖下载。工具目录可用不证明真实运行一定成功；doctor 只核结构前提，实际 JDK/Maven probe 和测试在 build 内完成。

run 要求全新仓库外绝对目录，保存单写者锁和 state.json。身份包括请求原字节、Python主次版本、当前实现与清单内案例输入/回执字节；目录意外文件在读取正文或摘要前拒绝。run_id 和完成前缀不随 resume 重建。

| 状态 | 含义与接续 |
| --- | --- |
| READY | 前检已完成、动作未发起，可安全 resume |
| RUNNING / UNKNOWN | 动作已开始或结果未明，resume 返回 UNKNOWN，不自动重放 |
| SUCCEEDED | 此案例程序按其合同完成，重复 resume 只读回结果 |
| FAILED | 已知运行失败，重复 resume 不自动重试 |

跨进程暂停只支持 `--pause-after-preflight` 这个明确安全点；不恢复中途 Maven 或任意阶段。输入/实现变化拒绝续跑；已有 writer.lock 不自动清除或抢占，先查原执行者。状态存储假设目录受信任，文件锁和原子替换不提供恶意进程隔离、跨主机全局锁、断电事务或日志防篡改。

程序退出0表示命令正常返回（包括 READY 或完成结果读回），失败/未知/环境不足为1，输入/协议/路径拒绝为2；显式用户中断沿宿主退出码（如130），在途状态仍保 UNKNOWN。SUCCEEDED 不合并子结果：结构通过、PARTIAL、NOT_RUN、作者分析与独立审查仍按原案例字段解释，不能当业务全部通过。

返回：[验证指南](validation-guide.md) · [项目入口](../README.md)。

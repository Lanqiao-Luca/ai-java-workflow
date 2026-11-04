# Loop 执行文件与案例

已填计划与实际控制输入同放本目录，状态分别说明；可复用格式见 [templates](../templates/README.md)。由[任务协调者](../../agents/task-coordinator.md)选择并执行，Brain 不直接调用。

- [整改执行文件](execution-plan.md)：已填虚构计划，NOT_RUN。
- [整改轨迹](review-convergence.md)与[控制输入](review-trace.json)：保留原案例范围。
- [巡检执行文件与程序](inspection/README.md)：本地虚构文件读取、补证和 PARTIAL。
- [缺陷执行文件与程序](defect/README.md)：整体验收、发现与证据状态转换。

责任 Agent 可分别运行 `python3 -B loops/examples/inspection/run.py` 和 `python3 -B loops/examples/defect/run.py`。它们执行 Loop 控制，不调用生产服务、模型或 Java 构建。

返回：[Loops](../README.md)。

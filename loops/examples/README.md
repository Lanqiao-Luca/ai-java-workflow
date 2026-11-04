**目的**：导航 Loop 的已填执行文件与案例，并区分计划、文档推演和真实控制执行。

**适用于**：Brain 选择 Loop 入口后定位案例的助手和使用者；底层方法由责任 Agent 使用。

# Loop 执行文件与案例

已填计划与实际控制输入同放本目录，状态分别说明；可复用格式见 [templates](../templates/README.md)。Brain 可直接选择 Loop 入口与案例，具体单轮和底层方法仍按 Workflow→Agent→Skill 交接，由当前[协调者](../../agents/task-coordinator.md)支持运行。

- [整改执行文件](execution-plan.md)：已填虚构计划，NOT_RUN。
- [整改轨迹](review-convergence.md)与[控制输入](review-trace.json)：保留原案例范围。
- [巡检执行文件与程序](inspection/README.md)：本地虚构文件读取、补证和 PARTIAL。
- [缺陷执行文件与程序](defect/README.md)：整体验收、发现与证据状态转换。

责任 Agent 可分别运行 `python3 -B loops/examples/inspection/run.py` 和 `python3 -B loops/examples/defect/run.py`。它们执行 Loop 控制，不调用生产服务、模型或 Java 构建。

返回：[Loops](../README.md)。

本导航现作为当前入口维护；[更新前原字节](../../docs/public-baseline/d3094e8e01285fe5355d897f57902c16e251f6a3d1e3a0a282037ad81b17d013.txt)保全，历史案例和回执未改。

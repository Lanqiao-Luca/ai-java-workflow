**目的**：导航本层已填执行文件、案例及各自真实验证边界。

**适用于**：由责任 Agent 选择 Workflow 资料的使用者；案例与历史回执不代当前任务验收。

# Workflow 执行文件与案例

本目录收录已填执行文件；[模板](../templates/README.md)保持空白。每个实例说明是实际执行、历史证据还是文档推演，不把填表当完成。

- [设计到模块贯通案例](design-to-modules/README.md)：设计发现/修订为文档推演，模块正例与四类拒绝为实际离线程序执行。
- [书签任务执行文件](bookmark-tags.md)：完整填写的虚构单轮计划，状态 NOT_RUN，供[任务协调者](../../agents/task-coordinator.md)按 [研发 Workflow](../java-spring-development.md)采用。
- [已有真实 Spring 执行案例](../../examples/workflow-bookmark-tags/README.md)：代码、测试、阶段 trace 与回执仍在原处，避免复制一份证据。

可由责任 Agent 按原案例前提运行 `python3 -B examples/workflow-bookmark-tags/run.py`；新填计划不会被该运行器自动消费。

返回：[Workflows](../README.md)。

本导航由旧版保全记录转为当前维护入口；[更新前原字节](../../docs/public-baseline/48a01a70932639a0500b64d9d23bd6d8f5d0f5bb62af3560de90ee4bc0e35bb3.txt)另存，原案例正文与运行回执未改。

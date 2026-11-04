**目的**：定位用于生成目标节点、依赖、门禁与收口执行计划的复用模板。

**适用于**：已接受任务并核本层合同的责任 Agent；模板不保存真实运行进度。

# Graph 模板

[执行计划模板](execution-plan.md)用于目标、依赖、写集、门禁与汇合。[任务协调者](../../agents/task-coordinator.md)实例化后选择当前支持的执行器，不由 Brain 直接启动。

Graph 组合 Loop 与 Workflow；单轮职责见 [Workflow 合同](../../workflows/java-spring-development.md)。填写后的执行文件和真实控制输入见 [examples](../examples/README.md)。本 Markdown 模板不是运行器 JSON 格式；采用 JSON 后端时仍须遵守所选 Graph 的定义校验合同。

返回：[Graphs](../README.md)。

**目的**：定位用于生成单轮阶段、责任与失败返回执行计划的复用模板。

**适用于**：已接受任务并核本层合同的责任 Agent；模板不保存真实运行进度。

# Workflow 模板

[技术设计计划](technical-design.md)与[模块规划计划](module-planning.md)供对应职责绑定当前候选、来源、阶段、预算和恢复点。

[执行计划模板](execution-plan.md)供[任务协调者](../../agents/task-coordinator.md)实例化单轮任务；阶段职责沿 [Java/Spring Workflow](../java-spring-development.md)承接。模板定义阶段、输入输出和失败返回，不保存某次任务进度。

填写后的公开执行文件见 [examples](../examples/README.md)。真实工程实例保存在使用者授权的位置，不回填模板，也不复制私有运行记录到公共案例。

返回：[Workflows](../README.md)。

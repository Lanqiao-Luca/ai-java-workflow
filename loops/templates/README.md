**目的**：定位用于生成多轮预算、继续停止与恢复执行计划的复用模板。

**适用于**：已接受任务并核本层合同的责任 Agent；模板不保存真实运行进度。

# Loop 模板

Brain 可以选择 Loop 入口与模板，由当前[协调者](../../agents/task-coordinator.md)或宿主按合同实例化和推进；Loop 组织同一目标的多轮 Workflow，模板本身不启动循环。

- [执行计划模板](execution-plan.md)：目标、单轮合同、预算、停止和恢复。
- [技术重试记录](technical-retry.md)：尝试次数与受理未知。
- [整改收敛记录](review-convergence.md)：发现、证据失效与独立关闭。

填写后的执行文件及可运行控制案例见 [examples](../examples/README.md)。实际任务记录保存在使用者授权的位置。

返回：[Loops](../README.md)。

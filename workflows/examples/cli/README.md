**目的**：提供统一命令入口的已填离线请求，明确执行与接续的实际范围。

**适用于**：[任务协调者](../../../agents/task-coordinator.md)按[命令合同](../../../docs/cli.md)采用受信案例；JSON 是实例请求，不是任意工程定义。

# 统一命令请求

challenge.json、local.json、modules.json、benchmark.json 分别执行固定反证、本地文件采集、模块控制和结构基准案例。`run --pause-after-preflight` 后可由新进程 `resume`；保原 run_id、输入及实现身份，成功不重跑，未知不重放。

Spring 请求需使用者填入明确的 JDK/Maven 和仓库外依赖缓存路径，见命令合同。模板不包含本机路径，实际结果由调用方运行目录保存，不写进本目录。

实际跨进程和负例由 `tests/test_workflow_entry.py`执行，无模型或新Java构建；真实 Spring 的命令适配另以本轮实际运行核证。

返回：[Workflow 案例](../README.md)。

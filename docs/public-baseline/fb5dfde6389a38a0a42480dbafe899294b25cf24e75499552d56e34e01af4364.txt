---
name: workspace-isolation
description: 按执行实例准备、核验和回收worktree与实际sandbox，缺后端时拒绝，不把目录当隔离。
---

# 工作区隔离

目的：把当前任务范围适配到可验证的实例资源，不创建新的目标、权限或上层Graph。

## 适用与输入

需要并发写入或保护现有工作区时采用；输入为可信仓库、冻结提交、run_id/父子关系、运行根、工具只读根、写集与有限预算。调用者须明确这些目录和动作已授权。

## 共用方法

- [执行实例隔离](../../standards/workspace-isolation.md)
- [并发与候选合同](../../standards/concurrent-execution.md)

## 实际步骤

1. 核来源和干净快照；不stash用户改动，也不凭HEAD猜未提交代码。当前实现拒属性过滤器、子模块和符号链接来源。
2. 通过宿主[资源机制](../../tools/execution/runtime.py)分配独立branch/worktree/HOME/TMP；不把宿主凭证、Git管理目录和相邻实例挂载给作业。
3. 调用实际macOS内核后端并探测读写/网络/Git/链接/派生进程边界；不支持即拒绝，未知不能填通过。
4. 执行已声明前台argv，单写状态和有限预算由宿主控制。当前默认禁止fork，Maven/Gradle等需要子进程的命令不可直接使用此后端。
5. 作业结束核字节/HEAD/index/写集；仅宿主提交，并在集成候选重验。回收只处理干净、身份一致的已停止资源。

## 输出与停止

交资源归属、探测、输入/输出提交、状态与未决；实际源码/日志默认私有，不因产出自动公开。超时/取消终止已知进程组；UNKNOWN占用不自动释放或重试，整个池隔离后需人工核外部状态。审计检查不等于自动续跑。

## 能力边界

仅已测macOS sandbox-exec实验前台后端，该命令已弃用；无Linux/Windows裸进程回退。文件元数据/根目录枚举及声明工具根只读允许，不提供恶意多租户、总RAM/总磁盘硬配额或宿主SIGKILL后自动进程回收保证。共享额度只覆盖采用同一runtime_root的本引擎实例；别的运行根和外部进程不计入。

具体案例由上层Graph组织：[Graph案例](../../examples/concurrent-java-graph/README.md)。返回：[Skills](../README.md)。

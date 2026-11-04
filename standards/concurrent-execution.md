---
atom_nature: operation
atom_secondary_natures: []
atom_applicability: domain
atom_scope_detail: 仅适用于本文声明的任务、消费者和必要前提
maintenance_role: canonical
atom_domain: 受控并发执行
---
**目的**：约束并发执行的来源、依赖、候选与资源身份，使结果可核对。

**适用于**：供当前方法的责任 Agent、作者与审查者使用；一个Graph需要调度多个可独立执行的Workflow时。

# Graph与Workflow并发合同

## 适用条件

一个Graph需要调度多个可独立执行的Workflow时。

## 输入

冻结定义/DAG、base commit、父子run_id、每Graph上限、共享runtime根的宿主容量和精确成功行。

## 操作步骤

按执行实例命名，不能按文件名复用运行状态；依赖成功才启动。各Graph子任务共享额度，同一运行根再以持久文件租约限制实际进程数。宿主单写各Graph状态，Git管理串行；把依赖的精确commit合入新实例，合并后重验。成功前核被测试工作区字节、HEAD、暂存区和逻辑写集，漂移不提升。

## 输出

实例状态、分支/提交、合并候选、成功证据、失败/取消/UNKNOWN及资源回收结果。

## 角色职责

Graph组织依赖与汇合；Workflow承担已声明命令和验收；Agent职责合同不等于原生LLM调用。

## 验收方法

必须证明实际重叠及上限、依赖等待、工作区/沙箱隔离、合并后验证和失败不提升；退出0缺精确成功行仍失败。

## 异常与停止

超时/取消/协调者异常先终止已知进程组再回收。禁止任务fork，避免setsid后代逃逸；宿主崩溃留下active容量时隔离整个池，不杀旧PID、不复用未知额度。inspect仅恢复审计，不自动重放或续跑。

本机制没有网络授权、自动发布或生产访问能力。返回：[Standards](README.md)。

# 从需求到并发集成的实际过程

1. 需求：TitlePolicy按trim拒绝null/空白；TagPolicy按trim去重保序、保留大小写、拒绝任一空白/null项。所有数据独立虚构，来源为本case seed源码。
2. 定义：Graph JSON引用3个具体Workflow JSON；每个声明实现者、代码实现/工作区隔离Skill、argv、写集、精确成功行和30秒预算。本宿主执行器只跑确定性命令，不声称原生AI角色自动实现。
3. 冻结：从3份Java seed创建无远程的新临时Git仓库，冻结base commit。原项目工作树不参与修改；本例没有未提交输入被隐式继承。
4. 资源：Graph和每个Workflow都有独立分支/worktree及实际Seatbelt配置，子run_id归parentGraph。prepare实测自身写成功，外部合成canary/Git管理目录/网络/链接访问和fork拒绝。
5. 并发：title和tags各写自己的Java文件，在各自JVM内独立编译与检查。每Graphmax_parallel=2，同runtime根的进程租约也为2，HOME/TMP不共享；不同图可共享该池。
6. 提升：任务成功后核精确marker、字节/HEAD/index/写集，宿主才commit。sandbox不能直接读写Git管理目录；并发不能绕过候选身份检查。
7. 汇合：integration新worktree从base开始，宿主串行合入两个精确commit，实际验证两个提交是其祖先。合并冲突不执行测试、不自动解冲突；成功则在新JVM内编译两组件并运行8断言。
8. 交付与回收：核实际并发区间重叠、依赖等待、全部probe和集成结果；源HEAD未变。仅回收已停止、身份未漂移且干净的4份worktree及可写HOME/TMP，保留私有状态/策略/日志及Git输出提交；演示夹具最终整体清理。

回归另覆盖失败后代阻断/独立继续、并发1、跨Graph共用池、取消、超时、fork拒绝、写集/候选漂移、冲突、脏保留与重复清理、UNKNOWN不重放和未知容量隔离。它们只使用本地临时虚构材料，不触发生产操作。

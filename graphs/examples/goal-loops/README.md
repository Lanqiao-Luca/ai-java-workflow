# 巡检与缺陷的双目标 Graph

本例实际执行[五节点定义](../../evidence-goals.json)、前台 Graph、已有[巡检 Loop](../../../loops/inspection-convergence.md)、[缺陷 Loop](../../../loops/defect-convergence.md)、确定性 Gate 和 closure。所有输入均为本目录独立构造的虚构文件；缺陷审查上下文和测试数字为模拟数据，不调用模型、不访问真实服务、不构建 Java 或部署。

## 一次运行三个控制案例

```sh
python3 -B graphs/examples/goal-loops/run.py
```

| 场景 | 实际控制结果 |
| --- | --- |
| complete | 两 Loop 并发派发：日志补读尾段，缺陷补齐行为/交接；两个 Gate 通过，closure 核全目标后 SUCCEEDED |
| partial | 未准入 API 不读取，未来构建来源也不预读；巡检保留完整三项及两个缺口。独立缺陷 Loop 和其 Gate 继续成功，整图仍 PARTIAL |
| unknown-effect | 缺陷原 demo-effect 结果 UNKNOWN，Loop HOLD，图 UNKNOWN；保留 operation_id/handle，不重跑或收口 |

聚合脚本退出 0 只表示三种预期控制结果均验证成立，不把负例的 PARTIAL/UNKNOWN 改成目标成功。单次操作入口的退出码另见下文。

complete 只表示原图定义的“证据收齐”和“指定缺陷验收”满足；模拟日志错误与 HTTP503 仍保留，不据此宣称服务健康或所有异常均已修复。partial 的来源准入限制属于巡检目标，独立缺陷目标只读自身获准的证据包，不转用其他工具读取被拒 API 文件。

## 保存检查点、暂停和接续

```sh
python3 -B scripts/run_goal_graph.py --run-root <仓库外全新私有目录>
python3 -B scripts/run_goal_graph.py --run-root <另一全新私有目录> --pause-after inspection
python3 -B scripts/run_goal_graph.py --run-root <刚才暂停的同一目录> --resume
```

首两条是独立示例，不复用已存在目录。默认 complete；`--scenario partial` 或 `--scenario unknown-effect` 选择相应负例。操作入口 SUCCEEDED 退出 0、PARTIAL/UNKNOWN/失败退出 1、准入拒绝退出 2、PAUSED 退出 3。原预算/场景/输入/代码必须一致；初轮并发的两 Loop 都返回后才暂停，恢复只续 Gate 与 closure，不重跑两 Loop。

运行器使用真实墙钟，暂停时间计入原截止；默认本例总预算 20 秒，可显式给 `--budget-seconds`，恢复时保持原值。内层 Loop 只使用外层剩余预算。每个 observed_at 是本次读取虚构文件的时点，不是线上业务发生时间；存储响应与构建报告都不代表真正发起请求或构建。

冻结源文件 SHA 和实际适配器代码/配置身份绑定当前运行；未获准/未来来源连预读都不发生。后续输入变更会拒绝原检查点，不通过新目录清零原业务预算。节点产品、原发现、模拟关闭证明和 Gate 快照保存在私有根的 state.json/products，不直接上传运行目录。

[场景](scenarios.json) · [通用合同](../../goal-graph.md) · [Graph 状态](../../../docs/graph-status.md) · [案例入口](../README.md)

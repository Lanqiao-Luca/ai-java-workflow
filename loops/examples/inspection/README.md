# 虚构巡检的补证与部分退出

本例实际读取本目录日志、接口响应 JSON 与构建报告 JSON，再运行[巡检控制器](../../../tools/inspection_loop.py)。所有文件和时钟均为独立构造的模拟材料，不查询真实服务、不调用模型、不执行 Java 构建。

```sh
python3 -B loops/examples/inspection/run.py
```

`supplement` 首轮日志只有窗口前段，返回 MISSING 及 tail 补证步骤；接口与构建已覆盖。第二轮只读日志后段，不重复已完成来源，最终 CONVERGED。日志含模拟错误，接口报告 HTTP503；这些异常仍保留，收齐证据不表示系统健康。

`partial` 的接口未获读取许可，控制器不调用该来源；日志正常取得，构建报告需未来时点，当前不等待或调度。输出 PARTIAL，原三个必查项仍在 required，missing 保留 api-response 和 build-report，已有日志结果可独立交付。

候选身份来自 `candidate.json` 的真实文件 SHA；需求身份来自完整必查集合，规则身份来自当前控制器文件 SHA。每份已读原件计算 SHA 留在观察记录中；时点 1000–1025 是虚构控制时钟，不是本机或生产观察时间。`build-report.json` 的测试数字仅为模拟记录，不作为实际构建通过的证据。

[场景声明](scenarios.json) · [方法](../../inspection-convergence.md) · [Loops](../../README.md)

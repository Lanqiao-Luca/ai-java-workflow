**目的**：实际读取两份独立虚构文件，验证本地来源适配与原覆盖判定、反证职责的交接。

**适用于**：POSIX、Python 3.9+ 本地离线演练；不代表生产日志读取或任意目录扫描许可。

# 本地来源案例

[证据采集者](../../../agents/evidence-collector.md)沿[取证 Workflow](../../evidence-collection.md)采用本案例。`scope.json` 固定 fixtures 内两份 UTF-8 文本的相对路径、原字节 SHA、目标、正控制与预算；根目录由调用方显式传入。没有递归或自动发现。

```sh
python3 -B workflows/examples/local-evidence/run.py
python3 -B -m unittest discover -s tests -p test_local_evidence.py -v
```

实际执行 complete 命中、sample 命中、有正控制的集合内零命中、页预算 PARTIAL 四种路径。输出保原字节身份与行投影；空行不投影但不改写文件或原摘要，页游标使用下一明确文件路径。

采集结果可作为[结论复核者](../../../agents/conclusion-reviewer.md)的事实输入，需另行填写解释、矩阵、实际反证和敏感性；工具不自动把文件内容解释成根因。Q1 的缓存运行案例继续核其真实执行观察，本案例不会把静态文件冒充运行证据。

变化返回 STALE，缺文件 UNKNOWN，拒权 DENIED，链接/非普通文件/非文本 REJECTED；均不作为业务零条。全量仅指明确批准文件集合；已知摘要不证明现实来源或权限。根目录父级与宿主受信任，无 Windows 后端、网络连接器或恶意进程完整隔离保证。

返回：[案例目录](../README.md)。

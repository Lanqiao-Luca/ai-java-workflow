candidate_id: 2986559d3612bcca8fa0d4c63bd6c1c70890856c1abe10f71d1773dc73dededf

# 标签规范化原则审查

结论：PASSED，限本候选的范围、来源声明、证据一致性和职责边界。未发现阻塞性原则违反或缺失必要的候选绑定证据。本阶段是与实现、验证分离的原生审查上下文，未执行 Java 测试；本结论不替代代码审查、独立功能验收、业务采用或发布许可。

## 输入、身份与证据层次

实际工作目录为当前 `instances/principle_review` 工作区；只写本文件。读取 [task.md](task.md)、[requirements.md](requirements.md)、[implementation.md](implementation.md)、[verification.md](verification.md)、宿主 [validation.json](validation.json)，以及当前 POM、全部三个生产类和三套测试源码。没有读取相邻实例或无关私人资料。

首行候选身份取自 host validation.json，随后实际重算：对 `app/pom.xml` 与 `app/src` 下全部文件逐一 SHA256，构造相对路径到摘要的映射，再对 `json.dumps(mapping, sort_keys=True)` 的 UTF-8 字节 SHA256。9 项映射与 host 的 `source_sha256` 完全相等，计算结果与 host 的 `candidate_id` 及 verification.md 首行完全相等。身份包含测试和测试资源，Markdown 不参与；没有复用旧候选身份。

host 报告为 `PASSED`、`category: passed`、`synthetic: true`、`offline: true`、`contract_complete: true`、`process_exit: 0`，列出 25 个测试，无失败、错误或跳过。逐测试源码提取 `@Test` 方法后与报告的完整 `test_names` 集合相等：固定 13、作者 7、独立验证 5。此核对证明报告与当前源文件及测试名称一致，不等于本阶段重跑了 25 项测试。运行证据由宿主报告承载，verification.md 为前阶段执行及解释记录。

本实例没有 `.build` 和 `verify.py`：文件清点时相应命令返回非零，已明确记录而未虚构读取构建日志或验证器。本阶段按审查合同使用 host validation.json，故这不构成缺失必要输入，也不为补日志访问其他实例。无法在此独立重查 Surefire XML、构建工具版本或前阶段命令历史。

## 四态原则判断

| 原则与适用性 | 判定 | 具体证据、反例和边界 |
| --- | --- | --- |
| 成果支持原目标 | 符合 | 服务顺序执行 `trim()`、`toLowerCase(Locale.ROOT)`、最终 UTF-16 长度检查，并用局部 `LinkedHashSet` 去重保序、限制四项。控制器调用同一服务并把校验异常映射为 400。没有引入排序、Unicode 等价化、存储或其他业务目标。 |
| 当前候选范围 | 符合 | 当前仅三个生产 Java 类，DTO 为控制器内部 record；POM 为 Java 17 / Boot 3.5.16。额外代码是允许的作者及独立验证测试。此阶段仅生成本报告，不改代码、固定测试、catalog、配置或验证器。 |
| 历史写集与基线保持 | 证据不足，非当前阻塞 | 实现说明明确没有事前哈希，不以事后哈希证明历史未改动；当前 POM、固定测试及资源摘要与实现说明记录一致。没有历史差异快照，故不能独立证明各阶段过去仅写声明文件，也不能声称新旧实现等价。若需要历史写集认证，由宿主补冻结基线和阶段差异，不由本角色执行 Git。 |
| 独立虚构来源与公开边界 | 符合于给定材料；历史来源保留未知 | task.md 明确为独立构造教学接口；当前源码和测试仅含标签、字符边界及通用框架，无真实客户、账户、凭证、公司服务坐标或业务记录。仅使用本工作区材料，未借案例模拟批准扩权。`synthetic: true` 与内容一致，但标志本身不能证明作者全部历史来源；没有读取私人资料来追溯。此结论不构成对外发布授权或法律许可。 |
| 行为保持与共享影响 | 符合于明确契约 | 服务仅读取调用者列表，中间集合局部化，完成后返回列表；HTTP 与直接服务调用共用算法。固定和扩展测试对应成功/失败输入保持、后续调用无残留、四项满额后的无效输入、UTF-16 与小写扩长。没有可变实例状态或外部调用。 |
| 完成声明与同一候选证据 | 符合 | requirements.md 明示未实现未运行；implementation.md 明示作者静态自查、测试待运行；verification.md 才声明 25 项运行通过，并与 host 的当前候选、计数、测试名称和零失败状态一致。早期文档无最终候选身份符合其非验证阶段定位，不冒充最终构建证据。 |
| 自查、验证和审查分工 | 符合 | 实现文档标作者自查；独立验证测试单独列 5 项，本审查只核原则和证据，不改验收或重签功能通过。Skill 文档仅作为方法来源，不把阅读案例称为启动案例中的进程。没有其他审查产物可供本阶段核实，故不声明代码审查已完成。 |
| 工具与执行权限 | 符合于本阶段实证 | 实际仅本地读取、SHA/JSON/测试名静态核对和写本报告。没有 Git、网络、HTTP 监听、公司服务、后台流程、发布或部署。前阶段 offline 构建是其报告和宿主证据所述，不冒称亲见全部进程。 |
| 数据库事务回滚、生产身份及部署验收 | 不适用 | 本任务明确无数据库或持久副作用，仅内存算法和 MOCK Spring/MockMvc；当前代码无相应操作。不是数据库、生产环境或真实端口已经验证通过。 |
| 全部业务/资源安全和平台隔离 | 证据不足／职责范围外 | 25 项测试及源码静态结构不证明无限输入、并发压力、资源耗尽、内核 sandbox、清理机制、真实网络或完整 Unicode 空间。verification.md 已保留这些 NOT_RUN，未将 150 项重复输入误写为性能验收。 |

已证违反：无。具体非阻塞限度为缺少历史差异证据、原始 Surefire/构建日志及来源历史认证；这些未被现有产物宣称已独立证明。

## 实际方法与操作记录

实际采用 [principle-reviewer 职责合同](../../../agents/principle-reviewer.md)，经 [principle-review Skill](../../../skills/principle-review/SKILL.md) 消费 [principles 标准](../../../standards/principles.md)：先界定当前授权和候选，再逐项列正反证，区分违反与缺证，最后按完成声明回查同候选证据。遵循 [../../../AGENTS.md](../../../AGENTS.md) 的来源和职责约束；精确写集优先，未更新 catalog manifest。

已实际阅读 Skill 的 example.md、所链接独立虚构案例的 README、case.json、trace.md、proposal.json、principle-report.md、corrected-proposal.json、follow-up.md 和 result.md。消费其“拟动作超写集”和“NOT_RUN 却声称通过”两个反例：本任务无对应矛盾；没有将案例中的整改或模拟结论移植为本任务证据。

实际工具为 `exec_command` 和 `apply_patch`，通过 `functions.exec` 调用；独立读取用 `Promise.allSettled` 批量等待并检查全部返回值，没有启动子 Agent。执行命令类别和精确读取范围如下：

```sh
pwd && rg --files -g 'AGENTS.md' -g 'task.md' -g '*requirements*' -g '*implementation*' -g '*verification*' -g 'validation.json' -g 'principle-reviewer.md' -g 'SKILL.md' -g '*standard*' -g '*review*' -g 'pom.xml' -g 'verify.py'
cat ../../../agents/principle-reviewer.md ../../../AGENTS.md task.md
cat requirements.md implementation.md verification.md validation.json
rg --files app .build ../../../skills/principle-review ../../../standards
cat ../../../skills/principle-review/SKILL.md ../../../standards/principles.md ../../../skills/principle-review/example.md
cat app/pom.xml app/src/main/java/example/nativeflow/*.java app/src/test/java/example/nativeflow/*.java
rg --files -g '!../../../**' -g '!.git/**' && sed -n '1,240p' verify.py
cat ../../../examples/review-scope-and-evidence/README.md && rg --files ../../../examples/review-scope-and-evidence && cat implementation.md
cat ../../../examples/review-scope-and-evidence/case.json ../../../examples/review-scope-and-evidence/trace.md ../../../examples/review-scope-and-evidence/proposal.json ../../../examples/review-scope-and-evidence/principle-report.md ../../../examples/review-scope-and-evidence/corrected-proposal.json ../../../examples/review-scope-and-evidence/follow-up.md ../../../examples/review-scope-and-evidence/result.md
```

其中 `.build` 清点退出 2，`sed` 读取不存在的 verify.py 退出 1，其余上述读取退出 0；没有把非零读取结果隐藏为成功。另执行 `python3 -B - <<'PY' ... PY` 只读脚本，使用 pathlib/hashlib/json 重算上述 9 文件身份，使用正则提取测试方法，断言映射、首行身份、25 项测试名和 host 状态一致，并检查三个生产类及本地构建材料存在性；退出 0。未运行 Maven、JUnit、MockMvc 或验证器。使用 `apply_patch` 仅创建本文件，随后回读并重算候选作最终静态自查。

## 交接与失效条件

无需收回当前完成声明或整改代码；下一接收者为交付职责及任务负责人，应连同其他必要审查保留本报告和 host 证据，仅在当前授权范围内交付，不自动提交、发布或部署。若 POM 或 src 任意字节变化，本候选绑定失效，须重新验证并定向复核；如果扩大到生产、数据库、真实监听或性能承诺，先补相应授权、契约和真实证据。本报告中的静态审查通过不能补齐这些未知。

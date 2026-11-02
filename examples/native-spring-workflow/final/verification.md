candidate_id: 2986559d3612bcca8fa0d4c63bd6c1c70890856c1abe10f71d1773dc73dededf

# 标签规范化独立验证

本阶段结果：PASSED。`python3 -B verify.py --offline` 实际退出 0；最终 [.build/validation.json](validation.json) 为 `PASSED`、`category: passed`、`process_exit: 0`、`offline: true`、`contract_complete: true`。25 个 JUnit 测试实际执行，失败 0、错误 0、跳过 0。本结论限于当前候选的内存算法、真实 Spring 测试上下文装配及 MockMvc 行为。

## 候选、职责与环境

工作目录为本 verification 实例，输入为 [task.md](task.md)、[requirements.md](requirements.md)、[implementation.md](implementation.md)、当前 POM、三个生产类、13 项固定测试和 7 项作者测试。需求与实现文档的静态说明没有被当成运行证据。当前为与实现阶段分离的原生验证上下文；新增测试由本验证者设计，不修改作者测试或业务代码。

首行身份取自本阶段最终实际运行产生的 `.build/validation.json`。随后用 Python 对 `app/pom.xml` 和 `app/src` 全部文件逐个计算 SHA256，将相对路径到摘要的映射按 `json.dumps(mapping, sort_keys=True)` 序列化后再计算 SHA256，核得与报告的 `source_sha256` 和 `candidate_id` 均完全一致。身份包含新增独立测试及测试资源；Markdown 不参与该摘要。验证器同时核对构建前后源文件映射未变化。未复用旧身份或 host validation.json。

固定入口沿用现有 Spring Boot 3.5.16 POM；Surefire XML 的实际运行属性显示 Java 17.0.21、语言规范版本 17。未探测或声称 Maven 的具体版本。读取冻结 `verify.py` 确认它从既定配置选择显式 Java、Maven 与预热公共缓存，创建最小子进程环境和私有构建目录，并运行 Maven `clean test`；本次 `--offline` 只允许缓存解析，不下载依赖。默认构建超时上限 240 秒，本次没有超时。没有修改运行配置、工具、缓存配置或验证器。

## 验收到断言

下表的 C、A、I 分别指 `LabelContractTest`、`ImplementationTest`、`IndependentVerificationTest`。全部列出的测试已在同一最终候选执行通过。HTTP 成功均观察规范化列表；拒绝按约定观察 400，不限制错误体格式。服务保持性比较调用前后完整输入列表。

| 验收 | 实际断言与用例 | 结论 |
| --- | --- | --- |
| Spring Bean 与 POST 接线 | C.`springBeanAndControllerAreWired` 真实装配服务、MockMvc 请求 200 与 `blue`；I 也注入真实服务、ObjectMapper 与 MockMvc | 通过 |
| 精确 trim 后 ROOT 小写、首次顺序 | C.`trimCaseAndStableDeduplication` 精确列表；C.`rootLocaleSurvivesTurkishDefault` 临时切换土耳其默认 Locale 并恢复 | 通过 |
| U+0000–U+0020 边界与空项拒绝 | I.`everyCharacterThroughU0020IsTrimmedAndAnEmptyResultIsRejected` 遍历 33 个代码单元，每轮检查服务结果、原输入、HTTP 精确成功列表及有效前缀后仅边界字符的 HTTP400 | 通过；循环仍计为 1 个 JUnit 测试 |
| 不扩展 trim、不删内部字符 | A.`whitespaceAboveTrimBoundaryIsPreservedThroughJson` 保留 U+00A0、U+2003；A.`trimUsesJavaControlCharacterBoundaryAndPreservesInternalSpace` 保留内部空格 | 通过 |
| 按规范化字符串相等去重，不额外进行 Unicode 等价化 | I.`unicodeContextAndCanonicalDifferencesRemainStringDifferences` 检查 `ΟΣ` 与 `ος` 合并、`οσ` 独立、预组合 `é` 与 `e` 加组合重音独立，HTTP 和服务均为精确四项列表 | 通过 |
| 空列表有效 | C.`emptyListIsValid` HTTP200 与空列表 | 通过 |
| null 列表、null 项、trim 后空项整次拒绝 | C.`nullListIsRejected`、`nullItemIsRejected`、`blankItemRejectsWholeRequest` 均 HTTP400；I 的 lateInvalid 测试补充满四项后的 null/空项 | 通过 |
| 最终长度恰好 16 有效、17 拒绝，不截断 | C.`exactlySixteenCharactersAreAccepted` 精确 16 字符输出；C.`seventeenCharactersAreRejected` HTTP400 | 通过 |
| UTF-16 长度、小写扩长后检查 | C.`lengthIsCheckedAfterRootLowercase`；A.`supplementaryCharactersAreCountedAsUtf16Units`、`lowercaseExpansionIsAcceptedExactlyAtLimitAndRejectedAboveIt`；I.`mixedSupplementaryCharactersAndLowercaseExpansionUseFinalUtf16Length` 经 HTTP 验证 7 个 emoji 加 `İ` 小写后恰好 16 有效，加 `x` 后 17 拒绝 | 通过 |
| 最多四个不同标签，重复不占名额 | C.`duplicatesDoNotConsumeDistinctLimit`、`fifthDistinctLabelIsRejected`；I.`manyDuplicatesIncludingExpandedLowercaseDoNotUseDistinctSlots` 用 150 项输入观察精确四项及原列表保持，`İ` 与 `i` 加组合点合并 | 通过；150 项是数据规模，不是测试数 |
| 成功和失败均不修改调用者输入 | C.`callerInputListIsNotMutated`；A.`immutableInputAndRepeatedCallsRetainOrderWithoutSharedState`、`rejectionAfterValidPrefixLeavesCallerInputUntouched`；I 的 trim、manyDuplicates、lateInvalid 测试比较完整输入 | 通过 |
| 有效前缀后无部分成功，失败不影响后续调用 | A.`rejectedHttpRequestDoesNotLeakPartialResultsIntoNextCall`；I.`lateInvalidItemsAfterFourLabelsRejectWithoutChangingCallerOrNextRequest` 对 null、空项、17 字符、扩长超限、第 5 项五种输入逐一检查服务拒绝、输入保持、HTTP400 和下一请求精确 `fresh` | 通过 |
| 无持久副作用 | 静态读取三个生产类：仅请求内局部集合和返回值，无数据库、事件或外部调用；失败输入保持和后续调用测试提供内存行为证据 | 静态结构与有限运行证据；数据库事务不适用 |

新增测试不约束服务拒绝异常的具体类型，仅要求抛出运行时异常，并另行检查真实 HTTP400。未要求错误体字段、返回列表可修改性或额外的 JSON 策略，未将实现选择扩大为验收规则。

## 实际运行计数

计数来自最终 validation.json 的实际 testcase 名单，并逐套件读取 `.build/target/surefire-reports/TEST-*.xml` 交叉核对：

| 测试套件 | 实际测试 | 失败 | 错误 | 跳过 |
| --- | ---: | ---: | ---: | ---: |
| LabelContractTest（固定） | 13 | 0 | 0 | 0 |
| ImplementationTest（作者） | 7 | 0 | 0 | 0 |
| IndependentVerificationTest（本阶段） | 5 | 0 | 0 | 0 |
| 合计 | 25 | 0 | 0 | 0 |

独立测试源码有 5 个 `@Test` 标记，与实际执行数一致。Maven 实际完成生产编译、测试编译及测试执行；Spring MOCK 上下文和 MockMvc 接线由成功用例证明。本次没有编译失败、环境阻塞或断言失败；不需要修改实现、放宽或删除断言，也没有构建重试。

## 实际方法与操作

消费 [verifier 职责契约](../../../agents/verifier.md)、[verification Skill](../../../skills/verification/SKILL.md) 与其 [verification 标准](../../../standards/verification.md)：先从已确认验收选择能区分错误实现的边界，再运行冻结入口，最后按 testcase 和源身份解释结果。消费 [Java/Spring Skill](../../../skills/java-spring-check/SKILL.md) 及 [java-spring 标准](../../../standards/java-spring.md)：沿用实际 POM、真实 Bean 和 MOCK 容器，检查异常映射、集合保持和小写长度边界。事务、数据库和事件因无对应依赖与调用不适用。

读取了 verification Skill 的案例入口及其 README、input、coverage、verification-report、result，仅借鉴证据与 NOT_RUN 区分方法；该案例未运行 Java 的结论没有移植到本次。遵循 ../../../AGENTS.md，声明的精确写集优先，未修改 catalog manifest。Skill 是方法来源，真实独立上下文来自本次分离验证阶段，不把方法文档称为新启动的进程。

实际工具为 `exec_command`、`write_stdin`、`apply_patch`。实际命令与操作如下，全部在本实例执行：

```sh
pwd && rg --files -g 'AGENTS.md' -g 'task.md' -g 'verification.md' -g 'validation.json' -g '*.md' -g '*.java' -g 'pom.xml' -g 'verify.py'
cat ../../../AGENTS.md ../../../agents/verifier.md task.md requirements.md implementation.md
cat ../../../skills/verification/SKILL.md ../../../skills/java-spring-check/SKILL.md ../../../standards/verification.md ../../../standards/java-spring.md
cat app/pom.xml app/src/main/java/example/nativeflow/*.java app/src/test/java/example/nativeflow/*.java
cat verify.py ../../../skills/verification/example.md
cat ../../../examples/verify-bookmark-title/README.md ../../../examples/verify-bookmark-title/input.md ../../../examples/verify-bookmark-title/coverage.md ../../../examples/verify-bookmark-title/verification-report.md ../../../examples/verify-bookmark-title/result.md
python3 -B verify.py --offline
cat .build/validation.json
```

三组独立材料读取通过 `Promise.allSettled` 批量等待并检查结果，不是并行 Agent。使用 `apply_patch` 仅新增声明的独立测试和本说明。构建命令首次返回会话标识后，用 `write_stdin` 空输入取得最终退出 0 和 `PASSED tests=25 category=passed`。另实际执行 `python3 -B - <<'PY' ... PY` 只读脚本：用 pathlib/hashlib/json 重算当前源映射与身份并断言报告一致，用 ElementTree 读取各 Surefire XML 的测试、失败、错误、跳过及 Java 版本，并用字符串计数核新增 `@Test` 数量；脚本退出 0。最终文件自查再次核首行身份、当前源映射和报告一致并确认两个声明输出存在。

构建生成物只在私有 `.build` 使用，不列为交付输出。没有 Git 操作、读取相邻实例或无关私人资料、访问真实服务、启动监听、数据库访问、发布或部署。没有主动网络调用；构建明确为 offline。冻结运行器是受限构建方法，代码已明确其不是 OS sandbox；本阶段未验证内核隔离、资源配额或清理机制。

## NOT_RUN 与交接

以下保持 NOT_RUN：真实 HTTP 端口监听、外部网络集成、数据库、鉴权、部署、打包/JAR 验收、并发压力、超时注入、资源耗尽和无限规模输入。数据库事务回滚在当前无存储场景不适用。仅 150 项重复数据不构成性能验收；顺序调用不构成并发证明。

缺失字段、畸形 JSON、非字符串强制转换、额外字段和错误体格式的独立策略未由任务定义，本次未增加对应验收；保留框架默认行为为未专门验证。Unicode 测试覆盖明确样本和 trim 全部低位边界，不声称穷尽全部 Unicode 输入。

下一接收者为审查与交付职责：本次无待修复运行失败。后续以 host validation.json 核当前候选；若 POM 或 src 任意字节变化，应重新验证并刷新身份，不能沿用本报告声明。当前结果不替代后续代码审查、业务采用或发布授权。

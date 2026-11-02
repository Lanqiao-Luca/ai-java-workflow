# 标签规范化需求与实现交接

本阶段结论：已具备可实施的完整核心契约，无关键语义待确认。本文件仅为需求分析产物，未实现、构建或运行 Java；不代表功能验收通过。

## 来源、基线与职责

- 唯一业务决策来源为本工作区 [task.md](task.md)。任务明确说明这是独立构造的教学接口，不来自真实业务记录。本文的验收数据也仅由该契约构造；未读取公司资料或私人业务数据。
- 固定验收来源为 [LabelContractTest.java](app/src/test/java/example/nativeflow/LabelContractTest.java)，本阶段仅静态阅读，包含 13 个测试方法；测试不替代任务中的完整要求。
- [app/pom.xml](app/pom.xml) 已声明 Java 17、Spring Boot 3.5.16、Web 和测试依赖。文件清点未发现生产 Java 源码，也没有 task.md 之外的工作区阶段 Markdown 产物可复用；不能声称已存在可保持的运行行为。
- 当前阶段为 requirements，仅允许生成本文件。不修改生产代码、POM、固定测试、catalog、验证器或原生配置，不执行 Git、服务访问、发布或部署。
- 当前没有构建候选或 validation.json 的已验证身份。本阶段未生成或声称候选 SHA256；后续验证阶段须从实际最终构建获得候选身份，不能把本文当构建身份证据。

## 已确认决策与可实施范围

| 对象/触发 | 已确认行为与边界 | 依据 |
| --- | --- | --- |
| 环境与入口 | Java 17 / Spring Boot 3.5.16；包名 `example.nativeflow`；`DemoApplication` 为 Spring Boot 配置入口 | task.md、POM |
| 服务 | `LabelService.normalize(List<String>)` 为 Spring Bean 服务，可直接调用并得到规范化标签列表 | task.md、固定测试的服务调用 |
| HTTP | `LabelController` 提供 `POST /labels/normalize`，JSON 请求含 `labels`；成功 HTTP 200，JSON 响应含规范化后的 `labels` | task.md |
| 单项处理顺序 | 先 `String.trim()`，移除首尾不大于 U+0020 的字符；再 `toLowerCase(Locale.ROOT)`；不得替换为其他空白处理或默认区域转换 | task.md |
| 内容与长度 | trim 后不得为空；规范化结果按 Java `String.length()` 计数，最多 16 个 UTF-16 代码单元；小写化可能增长长度，故上限必须检查最终结果；不得截断 | task.md、`lengthIsCheckedAfterRootLowercase` |
| 集合语义 | 按规范化后的字符串相等性去重，保留首次出现顺序；最多 4 个不同标签；重复项不额外占名额；允许空列表 | task.md |
| 拒绝 | null 列表、null 项、trim 后空项、规范化结果过长、不同标签超过 4 个均使整次请求 HTTP 400；不返回部分成功列表 | task.md |
| 错误体 | HTTP 400 是可观察契约；错误响应体格式不限定，不新增错误码、消息或多错误优先级要求 | task.md |
| 状态与副作用 | 调用者持有输入列表，服务不得原地修改；无数据库或其他持久副作用；事务回滚验收不适用 | task.md |
| 文件边界 | 生产文件仅限上述三个类；DTO 可为控制器内部类型；实现者可另写 JUnit 测试 | task.md |

示例：`{"labels":["  Blue ","BLUE","green"]}` 返回 HTTP 200 与 `{"labels":["blue","green"]}`。内部字符不由 trim 改写；不增加排序、Unicode 规范化、字符白名单或按语言显示长度计数的规则。

## 保持项与范围外

保持已有 POM 的 Java/Spring 版本、固定公开包名/类名/服务方法与接口路径、固定验收测试及测试资源。必须保持调用者输入列表原值和顺序；失败同样不能通过原地修改输入实现。空列表有效、输出首次顺序稳定、重复不占不同标签名额，都属于必须保持的契约行为。

未提供旧生产实现或旧运行结果，因此“保持”限于上述明确契约和现有固定材料，不主张新旧实现等价。鉴权、用户归属、标签存储、并发版本、审计、数据库事务、外部 API、真实 HTTP 监听与部署均不在本次范围；不从示例案例引入书签、所有者或替换标签库语义。

## 可观察验收矩阵

下表均为待执行验收，不是本阶段运行结果。HTTP 场景使用 MockMvc；服务输入保持项直接调用 Spring Bean。

| 编号 | 输入/前置 | 可观察结果 | 固定测试对应 |
| --- | --- | --- | --- |
| A1 | Spring 测试上下文，`["Blue"]` | Bean 存在；接口 200，首项 `blue` | `springBeanAndControllerAreWired` |
| A2 | `[" Green ","BLUE","green"," blue "]` | 200，精确列表 `["green","blue"]`，保持首次顺序 | `trimCaseAndStableDeduplication` |
| A3 | `[]` | 200，`{"labels":[]}` | `emptyListIsValid` |
| A4 | `labels:null` | 整次请求 400 | `nullListIsRejected` |
| A5 | `["ok",null]` | 整次请求 400，无部分成功列表 | `nullItemIsRejected` |
| A6 | `["ok","  "]` | 整次请求 400，无部分成功列表 | `blankItemRejectsWholeRequest` |
| A7 | `["  ABCDEFGHIJKLMNOP  "]` | 200，`["abcdefghijklmnop"]`，恰好 16 长度有效 | `exactlySixteenCharactersAreAccepted` |
| A8 | `["abcdefghijklmnopq"]` | 400，不截断为 16 字符 | `seventeenCharactersAreRejected` |
| A9 | `["A"," a ","b","c","d","D"]` | 200，精确列表 `["a","b","c","d"]` | `duplicatesDoNotConsumeDistinctLimit` |
| A10 | `["a","b","c","d","e"]` | 整次请求 400 | `fifthDistinctLabelIsRejected` |
| A11 | JVM 默认 Locale 为 `tr-TR`，输入 `["I"]` | 200，`["i"]`；测试结束恢复原默认 Locale | `rootLocaleSurvivesTurkishDefault` |
| A12 | 16 个 U+0130 构成一个标签 | ROOT 小写后为 32 个 UTF-16 代码单元，400 | `lengthIsCheckedAfterRootLowercase` |
| A13 | 可变输入列表 `[" Blue ","BLUE","green"]`，调用服务 | 返回 `["blue","green"]`；输入列表与调用前相等 | `callerInputListIsNotMutated` |

固定测试之外、可由同一已决规则推导的边界建议留给实现者补测：

| 边界/反例 | 期望与用途 |
| --- | --- |
| 标签仅为 U+00A0 | trim 不删除它，应成功保留；区分 `String.trim()` 与更广泛的空白清理 |
| 一个标签为 8 个/9 个相同补充平面字符（如 U+1F600） | 前者长度 16 有效，后者长度 18 拒绝；区分 UTF-16 长度与码点数 |
| `["a b","ab"]` | 保留两个不同标签；不删除内部空格 |
| 有效前缀后跟超长项或第 5 个不同项，直接调用服务 | 拒绝且调用者列表仍完全不变；补足失败路径输入保持证据 |
| 不可修改输入列表 | 有效输入仍可返回结果；不得依赖修改原列表 |

这些边界没有新增业务规则，也未在本阶段执行。服务拒绝时具体异常类型不限定；HTTP 层必须映射为 400。缺失字段、畸形 JSON、非字符串类型及额外字段的独立策略未由任务明确指定，本文件不新增其契约；其中任何实际得到 null 列表的情况仍适用已确认的 null 拒绝规则。

## 实际方法、工具与证据限度

实际采用 [requirement-analyst 职责契约](../../../agents/requirement-analyst.md) 经 [requirement-clarification Skill](../../../skills/requirement-clarification/SKILL.md) 消费 [requirements 标准](../../../standards/requirements.md) 和 [principles 标准](../../../standards/principles.md)：先把任务拆成对象、触发、输入、结果与拒绝，再将已决规则映射到保持项和可观察验收；未知不写成决定。已阅读 Skill 的案例入口及其独立虚构案例 README、输入、决策、需求和结果，仅借鉴方法，不借用案例的模拟确认或业务规则。遵循 [../../../AGENTS.md](../../../AGENTS.md) 的来源和证据边界；固定写集优先，本阶段不更新 catalog 的 public-manifest.json。

本阶段实际命令如下，均在当前 requirements 工作区执行；使用 `exec_command`，没有网络请求或 Git 命令：

```sh
pwd && rg --files -g '!target' -g '!.git' -g '!.build'
cat task.md ../../../AGENTS.md ../../../agents/requirement-analyst.md ../../../skills/requirement-clarification/SKILL.md ../../../standards/requirements.md
cat ../../../standards/principles.md ../../../skills/requirement-clarification/example.md app/src/test/java/example/nativeflow/LabelContractTest.java app/pom.xml && rg --files -g '*.md' -g '!../../../**' -g '!.git/**' -g '!.build/**'
cat ../../../examples/clarify-bookmark-tags/README.md ../../../examples/clarify-bookmark-tags/input.md ../../../examples/clarify-bookmark-tags/decisions.md ../../../examples/clarify-bookmark-tags/requirements.md ../../../examples/clarify-bookmark-tags/result.md
```

使用 `apply_patch` 仅创建 requirements.md；随后使用下列只读命令核查产物：

```sh
cat requirements.md
```

以上为静态材料阅读、需求整理与作者自查。未运行 Maven、JUnit、MockMvc 或验证器，未启动 HTTP 监听，未产生 JAR 或构建证据，未进行独立功能审查。文档形成不能替代运行验收或发布授权。

## 交接

下一接收者为实现职责：可按已确认契约实现三个生产类并补充必要测试；不得修改固定测试。随后验证职责需执行内存算法和 MockMvc 验证并记录实际通过、失败、跳过及未覆盖项，再由审查和交付职责保留各自证据。当前无阻塞核心实现的未决问题；若后续需求变化，应保留原结论并依据新决定定向复核。

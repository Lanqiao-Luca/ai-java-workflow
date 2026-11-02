candidate_id: 2986559d3612bcca8fa0d4c63bd6c1c70890856c1abe10f71d1773dc73dededf

# 标签规范化交付报告

当前限定交付结论：PASSED。已形成符合 [task.md](task.md) 与 [requirements.md](requirements.md) 的源码候选；同候选的编译、25 项测试及两份独立上下文静态审查均有通过记录。交付对象是教学接口源码、测试和证据文档，运行覆盖限内存算法、Spring MOCK 测试上下文与 MockMvc。当前没有已部署服务或现场业务验收结果。

## 行为与制品身份

`LabelController` 提供 `POST /labels/normalize`，调用唯一的 `LabelService.normalize(List<String>)` Bean。输入 `{"labels":["  Blue ","BLUE","green"]}` 返回 HTTP 200 与 `{"labels":["blue","green"]}`。服务依次使用 `String.trim()`、`toLowerCase(Locale.ROOT)`，按最终字符串去重并保持首次顺序；允许空列表，最多四个不同标签，每项最终长度最多 16 个 Java UTF-16 代码单元。null 列表、null 项、trim 后空项、超长或第五个不同标签使整次请求返回 400；没有部分成功结果。输入列表只读，中间集合局部化，没有数据库、外部调用或持久副作用。

POM 身份为 `example.nativeflow:synthetic-label-normalizer:1.0.0`，声明 Java 17、Spring Boot 3.5.16。生产源码仅为 [DemoApplication.java](app/src/main/java/example/nativeflow/DemoApplication.java)、[LabelController.java](app/src/main/java/example/nativeflow/LabelController.java)、[LabelService.java](app/src/main/java/example/nativeflow/LabelService.java)；DTO 为控制器内部 record。配置入口没有 main，当前交付范围不含独立监听服务的启动能力验收。

本报告首行身份取自宿主 [validation.json](validation.json)，并在本阶段实际重算确认：`app/pom.xml` 加 `app/src` 下全部文件共 9 项，逐项 SHA256；对相对路径到摘要的映射执行 `json.dumps(mapping, sort_keys=True).encode()` 后再次 SHA256。逐文件映射与宿主 `source_sha256` 完全相等，摘要与宿主 `candidate_id` 及验证、两份审查的首行全部一致。身份包括测试与测试资源，Markdown 不参与。GAV 只是项目坐标；本次没有构建或交付 JAR、镜像及其摘要。

## 状态与实际结果

| 环节与责任 | 当前状态、证据与限度 |
| --- | --- |
| 需求与实现 | 已形成；[implementation.md](implementation.md) 是实现者历史时点的作者静态自查，其“未运行”声明没有被改写为运行证据 |
| 独立验证 | [verification.md](verification.md) 记录实际执行 `python3 -B verify.py --offline`，退出 0；Maven 完成 `clean test` 的生产编译、测试编译及 JUnit/MockMvc 执行，无重试或断言放宽 |
| 宿主运行回执 | validation.json 为 `PASSED`、`category: passed`、`process_exit: 0`、`offline: true`、`synthetic: true`、`contract_complete: true`；25 项测试，失败 0、错误 0、跳过 0 |
| 固定、作者、独立测试 | 分别 13、7、5 项。本阶段从当前测试源码提取方法名，与宿主完整测试名集合逐项核对一致；循环中的 33 个 trim 字符或 150 项重复输入不额外计测试数 |
| 代码、语义与文档审查 | [code-review.md](code-review.md) 为 PASSED，无必要整改项；是与作者、验证分离上下文的静态审查，三项职责由同一审查上下文承担，没有冒称三个独立审查进程 |
| 原则审查 | [principle-review.md](principle-review.md) 为 PASSED，无阻塞性原则违反；范围、来源声明与证据一致性通过，历史写集和来源历史仍保留证据限度 |
| 本阶段交付 | 只生成本文件；完成当前身份、测试名单、证据状态与接续条件的静态核对，没有重跑 Java 测试或进行新的独立功能验收 |
| 提交、推送、Release、部署与现场验收 | 本 synthetic Graph 内均未执行；报告形成不代表服务部署或公开发布 |

有限运行证据覆盖普通与全部 U+0000–U+0020 trim 边界、较高空白保留、土耳其默认 Locale、ROOT 小写扩长、UTF-16 补充字符、空列表、四项与第五项、重复不占额度，以及成功/失败输入保持、失败后后续请求无残留。两份审查用满四项后的坏尾项、八个 `İ`、混合 emoji 长度及 Unicode 字符串差异反查契约，未发现当前实现的违例反例。

本 delivery 实例不存在 `verify.py` 或 `.build/validation.json`，未读取原始 Surefire XML、Maven 日志或验证环境配置。运行结果由身份匹配的宿主回执承载，verification.md 描述其当时真实执行；本阶段不能独立认证原始日志、工具版本或全部命令历史。verification.md 记录 Surefire 属性为 Java 17.0.21，Maven 具体版本未探测；本报告没有新增版本认证。

## 复核与复现

在当前实例可以执行以下只读身份核对；这是本阶段实际成功执行的核对逻辑的精简复现，不运行 Java：

```sh
python3 -B - <<'PY'
from pathlib import Path
import hashlib, json
r = json.loads(Path('validation.json').read_text())
paths = [Path('app/pom.xml')] + sorted(Path('app/src').rglob('*'))
assert not any(p.is_symlink() for p in paths)
m = {p.as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
     for p in paths if p.is_file()}
ident = hashlib.sha256(json.dumps(m, sort_keys=True).encode()).hexdigest()
assert m == r['source_sha256'] and ident == r['candidate_id']
for name in ('verification.md', 'code-review.md', 'principle-review.md', 'delivery.md'):
    assert Path(name).read_text().splitlines()[0] == 'candidate_id: ' + ident
print(ident)
PY
```

重新执行完整构建应由验证职责在宿主准备的验证实例进行，前提是具备原冻结 `verify.py`、显式 Java/Maven/预热公共依赖缓存配置、相同 POM/src，以及该阶段的执行授权；当前 delivery 实例缺这些入口，不在此补写配置或调用其他实例。原实际命令及预期检查为：

```sh
python3 -B verify.py --offline
cat .build/validation.json
```

验证器的方法实现可静态查阅 [native_build.py](../../../tools/native_build.py)。它选择显式工具和缓存，用最小子进程环境执行离线 Maven `clean test`，默认超时 240 秒，核构建前后源映射与完整固定测试。复现时需检查真实退出码、25 项名称与零失败/错误/跳过，而非只看文件生成；新回执还须重新绑定当前候选。私有 `.build` 不列作交付产物，不公开原始日志。本阶段未执行上述构建复现命令。

## 剩余风险、接续与停止条件

真实 HTTP 监听、端口/代理/容器接入、鉴权、外部网络集成、数据库、部署和现场验收均为 NOT_RUN。数据库事务回滚在当前无持久副作用场景不适用；没有数据库验证通过声明。打包/JAR、并发压力、超时注入、资源耗尽及无限规模输入也为 NOT_RUN。重复输入可以很多，有限重复样例没有证明资源上限或性能；完整 Unicode 空间未穷尽。缺失字段、畸形 JSON、非字符串转换、额外字段及错误体格式的独立策略未由任务定义，未专门验证。

没有历史修改前快照，当前哈希不能证明全部历史写集或新旧运行等价；`synthetic: true` 与当前材料相符，也不能独立认证全部来源历史。未验证 OS sandbox、配额和清理机制；构建运行器源码明确不构成 OS sandbox。上述限度均未被记为已完成验收。

下一接收者为任务负责人/宿主。当前内存与 MockMvc 范围无待关闭必要发现，可接收同候选源码和证据。若 POM 或 src 任意字节变化，停止沿用当前通过结论，由实现者交修订、验证者重新构建并生成身份，再由相交审查职责定向复核；最早恢复点是新候选验证。无需执行部署回滚，因为本次未部署；出现证据不匹配时回到最后有同候选证据的状态，不覆盖旧记录。

实际项目的另行公开交付交给原生 `github_committer`，由其依据当前用户授权处理；本报告没有启动、委派或声称完成该动作，也不增加提交、推送、发布或部署许可。若未来扩大到服务器、数据库、生产身份或性能承诺，相关负责人先明确契约与授权，补对应真实运行证据，再安排制品身份、部署恢复与现场验收；本报告不作那些范围的就绪承诺。

## 本阶段方法与操作实录

实际采用 [delivery-planner 职责契约](../../../agents/delivery-planner.md)，经 [delivery-planning Skill](../../../skills/delivery-planning/SKILL.md) 消费 [delivery-planning 标准](../../../standards/delivery-planning.md)：先核同候选逐项证据，再分开源码、验证、独立审查、制品与现场状态，最后给责任、失效条件和最早恢复点。读取 Skill example.md 及所链接案例的 README、case.json、trace.md、inputs.json、status.md、plan.md、result.md；实际使用其“旧候选单测不能给新候选背书”和“计划不等于授权/部署”的方法，未借用教材模拟状态。读取 ../../../AGENTS.md；精确写集优先，不更新 catalog manifest。额外静态读取 shared-rules 标准，仅用于核当前控制器共用服务的既有说明，没有扩展实现职责。

工具为 `functions.exec` 下的 `exec_command`、`apply_patch`；独立只读调用使用 `Promise.allSettled` 等待并检查，没有启动子 Agent。实际使用命令类别及范围如下：

```sh
pwd && rg --files -g '!app/target/**' -g '!app/.build/**' -g '!**/.git/**' -g '!.build/**'
cat ../../../agents/delivery-planner.md ../../../AGENTS.md task.md
cat ../../../skills/delivery-planning/SKILL.md ../../../standards/delivery-planning.md ../../../skills/delivery-planning/example.md ../../../standards/shared-rules.md
cat requirements.md implementation.md verification.md
cat validation.json code-review.md principle-review.md
rg -n 'candidate|sha256|digest|source_hash|validation|def ' verify.py ../../../tools/native_build.py ../../../tools/native_flow.py ../../../examples/plan-evidence-gated-delivery/README.md ../../../examples/plan-evidence-gated-delivery/plan.md
cat app/pom.xml app/src/main/java/example/nativeflow/*.java
```

另用 `cat` 单独回读 validation.json、verification.md、code-review.md 及上述案例材料、native_build.py；用 `sed -n '22,64p' code-review.md` 和 `sed -n '1,56p' principle-review.md`、`sed -n '56,120p' principle-review.md` 补足较长批次的截断阅读。身份脚本通过 `python3 -B - <<'PY' ... PY` 执行，使用 pathlib/hashlib/json 重算身份，以正则提取测试方法并与宿主列表核对，枚举三个生产文件，确认私有报告与验证入口缺失。

实际非零操作有两项：上述 rg 因 verify.py 不存在退出 2；首个只读 Python 核对脚本因打印语句括号错误退出 1，未执行核对主体、未写文件，修正后原核对退出 0。其余材料读取成功；没有把读取失败或脚本语法失败当成 Java 测试失败或通过。使用 apply_patch 仅创建 delivery.md，随后只读核首行、候选与本报告链接。全过程没有 Git、网络或公司服务调用，没有读取相邻实例及无关私人资料，没有修改源码、测试、catalog、验证器、配置或后台流程，没有监听、发布及部署。

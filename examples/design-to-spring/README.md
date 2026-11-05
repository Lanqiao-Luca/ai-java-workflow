**目的**：保存新需求→设计→专业复核→模块→真实 Spring 实现的候选与实际验收证据。

**适用于**：本案例虚构内存阅读清单；实际运行需 JDK17+ 和 Maven3，公开构建依赖与临时输出独立于业务环境。

# 设计到真实 Spring：批量归档

[需求](requirements.md)→[设计](design.md)→[分离设计复核](design-review.json)→[合同](contract.json)/[模块计划](plan.json)→[Spring工程](app/pom.xml)→[实际运行回执](result.json)已贯通。模块包绑定设计原字节，3模块/5需求唯一主责与实际app写集一致。

```sh
python3 -B examples/design-to-spring/run.py --java-home <JDK目录> --maven-home <Maven目录> --repository <仓库外公开依赖缓存> --output <仓库外回执.json>
```

使用独立用户/全局 Maven 设置，只从公开 Central 取得固定 Spring Boot 3.5.16 依赖。可加 `--offline` 仅用已有依赖。运行器在临时目录分别构建故意错误的红色负控制和当前绿色实现，实际解析 Surefire 精确测试集合；运行产物和原日志不进源码目录。

实际结果：两版本各14测试；红控制准确3个“非法尾项不得部分修改”相关失败，绿候选14测试全部通过，无错误/跳过，包含真实Spring/MockMvc和两线程旧版本竞争。红控制是作者故意构造的反例，不是独立审查发现。当前候选修正为全量验证后提交；不伪造未知缺陷或整改记录。

真实分离审查上下文先审设计，再对冻结实现、测试和模块核对，且独立运行同一运行器：结果同样红14/指定3失败、绿14全过，[独立运行](independent-result.json)与[审查结论](implementation-review.json)绑定相同候选，未发现需整改缺陷。作者与独立结果都只接受本文限定范围。审查不注册全局原生角色；不是外部人审。

`tests/test_design_spring.py`仅核当前源码/设计/运行器与回执身份、模块和测试集合，不重新运行Java。真实构建须运行上述命令；不可将便携检查代替新候选构建。

本案例不连接真实认证或业务存储，不启动对外服务。

返回：[项目入口](../../README.md)。

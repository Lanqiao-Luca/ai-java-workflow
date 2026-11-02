# 虚构需求：标签规范化

这是独立构造的教学接口，不来自真实业务记录。实现 Java 17 / Spring Boot 3.5.16 项目。

提供 `POST /labels/normalize`，请求为 `{"labels":["  Blue ","BLUE","green"]}`，成功返回 HTTP 200 与 `{"labels":["blue","green"]}`。

已确认规则：

- 对每项先使用 Java `String.trim()` 去掉首尾不大于 U+0020 的空白，再使用 `Locale.ROOT` 小写化。
- 按规范化后的字符串去重，保留第一次出现的顺序。允许空列表，返回空列表。
- 最多四个不同的规范化标签；输入重复项不额外占名额。
- 每项规范化后最多16个Java UTF-16字符，长度按 `String.length()`；不得默默截断。
- null列表、null项、trim后空字符串、单项过长或不同标签过多，整次请求返回HTTP400；不返回部分成功列表。
- 输入列表由调用者持有，服务不得原地修改它；无数据库或其他持久副作用，事务回滚验收不适用。

固定公开接口供验证者使用：包名 `example.nativeflow`；`DemoApplication`为Spring Boot配置入口，`LabelService.normalize(List<String>)`为Spring Bean服务，`LabelController`提供上述接口。错误响应体格式不限定，必须是HTTP400。生产文件只允许这三个类；DTO可作为控制器内部类型。实现者可另写自己的JUnit测试。

本次仅内存算法与MockMvc验证。不得启动HTTP监听，不接数据库、公司服务或生产身份，不部署、不自行Git提交。需要保留独立需求、实现说明、验证、审查和交付证据。未运行的边界如实说明，不用JAR或文件存在代替测试。

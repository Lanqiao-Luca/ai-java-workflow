# 输入与固定对象

复用仓库公开的书签标题案例：`examples/bookmark-title/after/BookmarkService.java`、测试及运行器。
本例不复制另一份Java候选，也不连接真实应用。实际源码集合通过该案例artifact-manifest固定。

验收：标题trim并持久化、空白拒绝、所有者与版本保护、字段保持、审计和无变更行为。
已知环境：本次整理环境无可用JDK，Java入口真实返回NOT_RUN退出2；不能补造测试通过。

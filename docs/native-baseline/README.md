# 原生实跑的历史执行源码

两份 `.txt` 原件逐字保存提交 `99168c15cad7bd40cb6819c6f4b638f4416abb1e` 中的原生适配器与引擎，用于继续核对[历史六阶段实跑回执](../../examples/native-spring-workflow/evidence/runtime.json)中的源码 SHA。它们不是当前可执行入口。

[历史案例检查器](../../scripts/check_native_cases.py)对这两个逻辑源码路径使用本目录原件，其余身份检查保持原有约束。原始回执、候选、25 项 Spring 测试和案例运行脚本没有改写；历史通过不覆盖[新恢复控制器](../native-recovery.md)。当前代码通过自己的回归测试和 CI 验证。

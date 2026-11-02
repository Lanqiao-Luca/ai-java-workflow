# 从v1到v2的保持与变更

| 行为 | 处理与落点 | 用例/证据 |
| --- | --- | --- |
| 不存在、owner、版本检查及顺序 | 保持TagService.replace前置 | missingReferenceRejects、nonOwnerRejectsBeforeTagValidation、staleVersionRejectsWithoutMutation |
| null列表与[] | 保持拒绝/清空区分 | nullListRejectsWithoutMutation、emptyListClearsTags |
| null/空白单元素 | 明确修复normalize：filter静默丢弃→拒绝整次请求 | blankItemRejectsWholeRequest、nullItemRejectsWholeRequest，v1红/v2绿 |
| trim、区分大小写、去重保序 | 保持normalize语义，LinkedHashSet表达顺序 | normalizeDeduplicateAndPersist的真实get存储断言 |
| title/owner/savedSequence | 保持新对象字段复制 | normalizeDeduplicateAndPersist |
| 真变更版本/审计各增一次 | 保持写入后记录 | normalizeDeduplicateAndPersist、emptyListClearsTags |
| 无变更和过期重试 | 保持比较结果和版本保护 | normalizedNoopPreservesVersionAndAudit、repeatAtCurrentVersionIsNoop、staleRetryAfterSuccessRejects |
| Spring Bean/请求/错误映射 | 无装配变更，需实际验证 | SpringBootTest/AutoConfigureMockMvc，全13用例 |

此表是源码与测试映射；是否执行通过由evidence/runtime.json真实回执判断，不靠表格存在。

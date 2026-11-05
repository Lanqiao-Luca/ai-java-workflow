**目的**：固定并实际比较八个反证报告结构任务，保留初始判断、指标分母和脚本纠正观测。

**适用于**：[能力评估者](../../../agents/capability-evaluator.md)的离线演练；标注由作者给出，无真实模型、人工返工或业务效果测量。

# 反证报告结构基准

先固定 cases.json 的八个任务及判定理由，再对完全相同的输入运行 minimal_fields 和 contract_checker。前者是作者明确故意简化的字段存在检查，后者是现有报告合同校验；不代表外部产品、模型或用户原先方法。三项结构有效（包括同源组与明确 NOT_RUN），五项结构无效。

```sh
python3 -B workflows/examples/capability-benchmark/run.py
python3 -B -m unittest discover -s tests -p test_capability_benchmark.py -v
```

逐项 initial 判断与预设还原分开：只在初始调用完成且该任务标签为无效时，对双方都将输入还原成相同完整报告，再各调用一次。纠正定义与正确答案不送给策略；还原由评估脚本按预设执行，不是策略自己定位修复。每方实际5次脚本还原，不能据此推断减少人工返工。

缺陷检出为正类：漏检=无效却判有效，误报=有效却判无效。汇总列 tasks/evaluated/unknown/correct/misses/false_alarms/detected_defects；accuracy=correct/tasks（有未知则null），precision=检出/(检出+误报)，recall=检出/(检出+漏检)，零分母为null。实际计时为每次策略函数调用的 perf_counter_ns 差，排除导入和构造输入；单次微型耗时不作提速宣传。

[本次实际观测](result.json)绑定任务、策略、原报告和必要候选输入 SHA；保存每项初始结果、状态、耗时、脚本还原与完整汇总。策略异常保 UNKNOWN，纠正失败不能当成功，原记录可重算。此标签仅判结构有效，不表示因果结论可信或允许实施。

作者标签不是第三方真值；八个自选任务不表示普遍能力、统计显著性或工程收益。human_rework/model_cost/engineering_effect 均保 NOT_MEASURED；没有自动模型调用、生产采样或后台复跑。

返回：[案例目录](../README.md)。

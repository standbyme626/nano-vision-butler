# Prompt12I：可靠性 / 安全 / 压测验收

## 对应任务
- T13I

## 目标
固化回压与退化策略，完成可交付级稳定性与安全验收。

## 输出
- docs/edge/reliability_plan.md
- docs/edge/soak_test_report.md
- tests/integration/test_edge_reliability_flow.py
- scripts/edge_soak_test.sh

## 验收
- take_snapshot 成功率 >= 99%，P95 响应时间有明确阈值
- get_recent_clip 成功率 >= 98%，P95 生成时长有明确阈值
- event captured_at 到后端入库 P95 延迟有明确阈值
- heartbeat 连续 24h 无误报抖动
- 至少一次断网恢复演练通过并可补传关键事件
- 回压/退化策略生效：优先保 heartbeat 与关键事件

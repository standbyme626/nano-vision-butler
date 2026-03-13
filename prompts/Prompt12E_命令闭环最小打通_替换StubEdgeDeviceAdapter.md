# Prompt12E：命令闭环最小打通（替换后端 StubEdgeDeviceAdapter）

## 对应任务
- T13E

## 目标
让 /device/command/take-snapshot 与 /device/command/get-recent-clip 触发真实 edge 执行器，而非后端 stub。

## 输出
- src/services/device_service.py（接入真实 edge command client）
- src/services/edge_command_client.py
- tests/integration/test_device_command_edge_bridge.py

## 验收
- 后端命令可远程触发 edge 执行
- command_id/trace_id 可全链路追踪
- 不再依赖 StubEdgeDeviceAdapter 生成媒体结果

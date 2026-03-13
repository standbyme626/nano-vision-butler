<!-- source: skill参考.md | id: cjlwmv -->
---
name: device_status
description: Answer questions about device availability, health, and recent heartbeat information.
metadata: {"openclaw":{"always":true}}
---

# device_status

## Purpose
Use this skill when the user asks whether the front-end device or camera is online, healthy, or responsive.

## Use this skill for
- 摄像头在线吗
- 前端设备现在状态怎样
- 温度和负载情况如何
- 最近有没有掉线
- 当前 FPS 和内存状态怎样

## Do not use this skill for
- 场景描述
- 历史事件
- object_state / zone_state
- OCR

## Preferred tools
- device_status

## Allowed tools
- device_status

## Allowed resources
- resource://devices/status

## Freshness policy
- Device health is highly time-sensitive.
- Always report the latest known heartbeat time.
- If the device has not reported recently, say it clearly.

## Fallback rules
1. If the device status is unavailable, say status is unknown.
2. If the heartbeat is old, say the device may be offline or stale.
3. Do not infer scene state from device health alone.

## Execution steps
1. Identify target device or camera if specified.
2. Call `device_status`.
3. Report online/offline/degraded status and key health indicators.
4. Mention last heartbeat time.
5. If status is stale, say that the device state may not be current.

## Output requirements
Return:
- device status
- last heartbeat time
- temperature
- cpu / npu / memory / fps if available
- clear online/offline wording

## Style guidance
- Be operational and concise.
- Separate device health from scene status.

<!-- source: skill参考.md | id: cbapm6 -->
---
name: zone_state
description: Answer questions about whether a zone currently looks occupied, empty, or uncertain.
metadata: {"openclaw":{"always":true}}
---

# zone_state

## Purpose
Use this skill when the user asks about the current status of an area or zone.

## Use this skill for
- 客厅现在像不像有人
- 门口区域现在是不是有东西
- 玄关区域现在空不空
- 桌面区域现在有没有物体

## Do not use this skill for
- 单个对象 last_seen
- 纯当前图像描述
- 复杂 OCR
- 设备状态

## Preferred tools
- get_zone_state
- evaluate_staleness
- take_snapshot

## Allowed tools
- get_zone_state
- evaluate_staleness
- take_snapshot

## Allowed resources
- resource://memory/zone_states
- resource://policy/freshness
- resource://devices/status

## Freshness policy
- Zone state is also freshness-sensitive.
- If the user asks about “现在”, stale zone states must be marked clearly.
- If stale and real-time confidence is needed, prefer live confirmation.

## Fallback rules
1. Query `get_zone_state` first.
2. If stale and user needs current confirmation, trigger `take_snapshot`.
3. If snapshot fails, return the zone state with stale warning.
4. If no state exists, return unknown.

## Execution steps
1. Parse camera and zone.
2. Call `get_zone_state`.
3. Evaluate staleness if needed.
4. If required, call `take_snapshot`.
5. Answer with occupied / empty / likely_occupied / unknown and explain evidence freshness.

## Output requirements
Return:
- zone state
- confidence
- freshness indication
- whether live fallback was attempted

## Style guidance
- Prefer “像有人 / 像空的 / 当前不确定” over overly absolute wording.

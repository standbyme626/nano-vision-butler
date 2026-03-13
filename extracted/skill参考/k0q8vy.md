<!-- source: skill参考.md | id: k0q8vy -->
---
name: history_query
description: Answer questions about recent events, recent history, and time-bounded activity summaries.
metadata: {"openclaw":{"always":true}}
---

# history_query

## Purpose
Use this skill when the user asks what happened over a period of time, or requests a summary of recent activity.

## Use this skill for
- 最近门口发生了什么
- 今天下午有没有人来过
- 最近 1 小时客厅有什么动静
- 今天是否出现过快递
- 帮我总结一下最近事件

## Do not use this skill for
- 单张图片内容描述
- 只问当前状态的问题
- 单个对象的 last_seen
- 设备状态与健康信息

## Preferred tools
- query_recent_events
- get_zone_state

## Allowed tools
- query_recent_events
- get_zone_state
- evaluate_staleness

## Allowed resources
- resource://memory/events
- resource://memory/observations
- resource://memory/zone_states

## Freshness policy
- History answers are not required to be real-time.
- Prioritize explicit time ranges from the user.
- If the user says "最近", prefer a bounded recent window instead of unbounded history.

## Fallback rules
1. If the time range is ambiguous, infer a reasonable short recent range.
2. If there are no matching events, say so clearly.
3. If history is sparse, optionally supplement with current zone state as context.
4. Do not fabricate events that are not in the history.

## Execution steps
1. Parse the requested time range.
2. Call `query_recent_events`.
3. If useful, call `get_zone_state` for present context.
4. Summarize the timeline in descending importance.
5. Mention if the result is sparse or incomplete.

## Output requirements
Return:
- time range used
- key events
- whether events are direct records or sparse summary
- optional current-state addendum if helpful

## Style guidance
- Prefer a short timeline.
- Highlight significant changes first.
- Keep time references explicit.

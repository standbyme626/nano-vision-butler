<!-- source: skill参考.md | id: 2kni5n -->
---
name: object_state
description: Answer questions about whether an object is currently likely present, absent, or unknown.
metadata: {"openclaw":{"always":true}}
---

# object_state

## Purpose
Use this skill when the user asks whether an object is probably still present now.

## Use this skill for
- 杯子现在还在桌上吗
- 快递现在大概率还在门口吗
- 钥匙现在是不是还在那里
- 那个包裹现在还在不在

## Do not use this skill for
- last_seen 纯历史问题
- 纯当前画面描述
- 区域占用问题
- OCR

## Preferred tools
- get_object_state
- evaluate_staleness
- take_snapshot

## Allowed tools
- get_object_state
- evaluate_staleness
- take_snapshot

## Allowed resources
- resource://memory/object_states
- resource://policy/freshness
- resource://devices/status

## Freshness policy
- This skill is freshness-sensitive.
- If the result is stale and the user is asking about "现在", favor explicit stale wording or live fallback.
- Prefer recent evidence over old observations.

## Fallback rules
1. Call `get_object_state` first.
2. If state is stale and the question is highly real-time, call `take_snapshot`.
3. If live refresh is unavailable, return the stale result with a warning.
4. If there is no state record, say the status is unknown.

## Execution steps
1. Parse the target object and optional location hint.
2. Call `get_object_state`.
3. Call `evaluate_staleness` if needed.
4. If stale and user wants real-time certainty, trigger `take_snapshot`.
5. Answer with present / absent / unknown plus freshness context.

## Output requirements
Return:
- state_value
- confidence
- stale or non-stale
- evidence timestamp
- whether fallback was attempted

## Style guidance
- Use wording like “大概率还在 / 目前看更像不在 / 当前无法确认”.
- Do not pretend stale records are live truth.

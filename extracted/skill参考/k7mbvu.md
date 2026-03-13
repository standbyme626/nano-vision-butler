<!-- source: skill参考.md | id: k7mbvu -->
---
name: scene_query
description: Answer questions about the current scene, current view, or the latest image from a camera.
metadata: {"openclaw":{"always":true}}
---

# scene_query

## Purpose
Use this skill when the user asks what is currently visible in a camera view, a newly uploaded image, or a freshly captured snapshot.

## Use this skill for
- 现在门口是什么情况
- 客厅里现在有什么
- 看看这张图里有什么
- 现在桌面上有什么东西
- 帮我描述当前画面

## Do not use this skill for
- 历史事件查询
- last_seen 查询
- 需要明确 stale/freshness 说明的状态类问题
- 复杂 OCR / 字段抽取
- 设备状态查询

## Preferred tools
- take_snapshot
- describe_scene
- get_recent_clip

## Allowed tools
- take_snapshot
- describe_scene
- get_recent_clip

## Allowed resources
- resource://devices/status
- resource://memory/observations

## Freshness policy
- Prefer the newest snapshot.
- If the user asks about "现在", "此刻", or "当前", prioritize a fresh capture.
- If a fresh capture is unavailable, clearly say the answer is based on the latest available media.

## Fallback rules
1. If the user already uploaded an image, analyze that image first.
2. If no image is provided and the question is about current state, call `take_snapshot`.
3. If snapshot fails, explain that live confirmation is temporarily unavailable.
4. If only recent video is available, summarize based on recent clip.

## Execution steps
1. Determine whether the user refers to an uploaded image or a live camera.
2. If live camera is needed, call `take_snapshot`.
3. If scene description is needed, call `describe_scene` or pass the image to the model.
4. Summarize visible objects, people, and notable changes.
5. Keep the answer grounded in what is visible; do not infer long-term state unless explicitly asked.

## Output requirements
Return:
- a concise scene summary
- notable objects or people
- whether the answer is based on uploaded image, fresh snapshot, or recent clip
- if needed, mention limited certainty

## Style guidance
- Be direct and visual.
- Avoid overclaiming.
- Distinguish between "I can see" and "I infer".

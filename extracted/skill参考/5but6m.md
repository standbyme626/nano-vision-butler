<!-- source: skill参考.md | id: 5but6m -->
---
name: ocr_query
description: Read text from images, perform simple OCR directly, and use structured OCR tools for field extraction.
metadata: {"openclaw":{"always":true}}
---

# ocr_query

## Purpose
Use this skill when the user wants text reading, text extraction, or field extraction from an image or snapshot.

## Use this skill for
- 读一下这张图上的字
- 看看门口纸条写了什么
- 提取快递单上的编号
- 帮我识别标签内容
- 识别并结构化输出字段

## Do not use this skill for
- 纯场景描述且没有读字需求
- 历史事件总结
- 设备状态问题

## Preferred tools
- ocr_quick_read
- ocr_extract_fields
- take_snapshot

## Allowed tools
- ocr_quick_read
- ocr_extract_fields
- take_snapshot

## Allowed resources
- resource://memory/observations
- resource://memory/events

## Freshness policy
- If the user uploaded an image, operate on that image directly.
- If the user asks to read current text from a live scene, capture a fresh snapshot first.

## Fallback rules
1. If the request is simple reading, prefer direct model OCR or `ocr_quick_read`.
2. If the request asks for specific structured fields, use `ocr_extract_fields`.
3. If there is no current image and the request is live, call `take_snapshot`.
4. If OCR is low confidence, state uncertainty explicitly.

## Execution steps
1. Determine whether the user supplied an image or refers to a live camera.
2. Determine whether the task is free-form reading or structured extraction.
3. Use `ocr_quick_read` for general text reading.
4. Use `ocr_extract_fields` for structured extraction.
5. Return readable text plus field JSON if applicable.

## Output requirements
Return:
- recognized text
- extracted fields if applicable
- confidence / uncertainty note
- source image type (uploaded / snapshot / recent media)

## Style guidance
- Quote short recognized text where helpful.
- Keep structured fields separate from explanation.

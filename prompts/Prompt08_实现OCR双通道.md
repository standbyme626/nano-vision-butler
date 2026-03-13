<!-- source: 提示词.md | id: 5nlffx -->
你正在为 Vision Butler v5 实现正式 OCR 能力。

任务目标：
实现模型 OCR + 工具 OCR 双通道的后端能力。

需要创建或补齐：
- src/services/ocr_service.py
- /ocr/quick-read
- /ocr/extract-fields
- ocr_results 的写入逻辑
- OCR 结果与 observations / media_items 的关联逻辑

项目背景（必须遵守）：
1. 简单 OCR 可以由多模态模型直接完成。
2. 结构化 OCR、高价值抽取、需要入库的 OCR 结果必须经过工具化通道。
3. OCR 是正式能力，不是后续增强项。
4. OCR 结果不能只留在模型回答里，必须支持写入 ocr_results。
5. OCR 结果在需要时可以写 observation 或升级为 event。

必须实现的能力：
- quick_read(image_uri or media_id)
- extract_fields(image_uri or media_id, field_schema?)
- save_ocr_result(...)
- attach_ocr_result_to_observation(...)
- 可选：promote_ocr_to_event(...)

返回结构要求：
- raw_text
- fields_json
- boxes_json
- language
- confidence
- source_media_id
- ocr_mode（model_direct / tool_structured）

必须遵守：
1. 当前任务不要真实调用外部 OCR 平台，可用 adapter / interface 占位。
2. service 层必须能清晰区分 quick_read 和 extract_fields。
3. extract_fields 必须支持返回结构化 JSON。
4. 如果 media_id 不存在，要返回明确错误。
5. 路由层不写 OCR 逻辑。

建议输出：
- src/services/ocr_service.py
- src/routes_ocr.py
- tests/unit/test_ocr_service.py
- tests/integration/test_ocr_flow.py

建议路由：
- POST /ocr/quick-read
- POST /ocr/extract-fields

验收标准：
- quick_read 返回文本
- extract_fields 返回结构化字段
- ocr_results 正常入库
- 结果能关联 source_media_id
- 至少覆盖正常 / media 不存在 / OCR 失败 三类测试

完成后请：
1. 说明双通道 OCR 的边界
2. 说明何时只返回结果，何时写 observation/event
3. 列出返回 schema
4. 给出 quick_read 和 extract_fields 的请求示例

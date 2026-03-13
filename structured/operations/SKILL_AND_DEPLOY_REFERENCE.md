可以，下面我把这两份一起给你：

1. **`config/nanobot.config.json` 初版模板**
2. **7 个 `SKILL.md` 初版内容**

先说两句你可以直接放进文档里的总说明：

* nanobot 当前公开能力已经支持：用 `--config` 跑独立实例、`agents.defaults.workspace` 指定工作区、Telegram channel 接入、`allowFrom` 访问控制，以及通过 `tools.mcpServers` 挂本地/远程 MCP server；MCP server 同时支持 `command + args` 的 stdio 模式和 `url + headers` 的 HTTP 模式，还可单独设置 `toolTimeout`。([github.com](https://github.com/HKUDS/nanobot/blob/main/README.md?utm_source=chatgpt.com)) ([github.com](https://github.com/HKUDS/nanobot/security/policy?utm_source=chatgpt.com))
* Skill 这部分，我下面给你的写法采用的是**AgentSkills / OpenClaw 兼容风格**：一个技能一个目录，里面放 `SKILL.md`，顶部用 YAML frontmatter，正文写“何时使用、允许哪些工具、步骤是什么”。OpenClaw 官方技能文档就是这种格式，而 nanobot 仓库本身也明确存在 skills loader 和 bundled skills，所以这套写法非常适合作为你当前项目的首版模板。([docs.openclaw.ai](https://docs.openclaw.ai/zh-CN/tools/skills?utm_source=chatgpt.com)) ([github.com](https://github.com/HKUDS/nanobot/blob/main/README.md?utm_source=chatgpt.com))
* 另外，Qwen 的官方 Function Calling 和结构化输出文档都说明了：模型判断是否调用工具，应用侧执行工具，再把结果回灌给模型；如果要稳定生成 JSON，应该使用结构化输出模式。因此，下面这些 Skill 文本会明确引导模型“先判断，后调工具，并尽量输出结构化内容”。([help.aliyun.com](https://help.aliyun.com/zh/model-studio/qwen-function-calling?utm_source=chatgpt.com)) ([help.aliyun.com](https://help.aliyun.com/zh/model-studio/qwen-structured-output?utm_source=chatgpt.com))

---

# 一、`config/nanobot.config.json` 初版模板

下面这份是**可直接拿来改**的初版模板。
我尽量只用了 nanobot 当前公开能力里能确认的结构：`agents.defaults.workspace`、Telegram `token` / `allowFrom` / `replyToMessage`、`gateway.port`、`tools.mcpServers`、`toolTimeout`、`restrictToWorkspace`。
**唯一需要你按实际环境确认的是 provider 名称和模型接入方式**：因为你现在跑的是本地量化的 `qwen3.5-9bq4`，这通常是走本地 OpenAI-compatible 接口或自定义 provider；nanobot 最近确实在扩 provider registry 和 OpenAI-compatible provider，但具体 provider 名字要以你当前安装版本为准。([github.com](https://github.com/HKUDS/nanobot/blob/main/README.md?utm_source=chatgpt.com)) ([github.com](https://github.com/HKUDS/nanobot/releases?utm_source=chatgpt.com))

```text id="s7qhl4"
{
  "agents": {
    "defaults": {
      "workspace": "./gateway/nanobot_workspace",
      "model": "YOUR_QWEN_MODEL_NAME",
      "provider": "YOUR_PROVIDER_NAME"
    }
  },
  "channels": {
    "sendProgress": true,
    "sendToolHints": false,
    "telegram": {
      "enabled": true,
      "token": "YOUR_TELEGRAM_BOT_TOKEN",
      "allowFrom": [
        "YOUR_TELEGRAM_USER_ID"
      ],
      "replyToMessage": true
    }
  },
  "providers": {
    "YOUR_PROVIDER_NAME": {
      "apiKey": "DUMMY_OR_REAL_API_KEY",
      "apiBase": "http://127.0.0.1:8000/v1"
    }
  },
  "gateway": {
    "host": "0.0.0.0",
    "port": 18790,
    "heartbeat": {
      "enabled": true,
      "intervalS": 1800
    }
  },
  "tools": {
    "restrictToWorkspace": false,
    "mcpServers": {
      "vision-mcp": {
        "url": "http://127.0.0.1:8101/mcp",
        "toolTimeout": 60
      },
      "memory-mcp": {
        "url": "http://127.0.0.1:8102/mcp",
        "toolTimeout": 60
      },
      "state-policy-mcp": {
        "url": "http://127.0.0.1:8103/mcp",
        "toolTimeout": 60
      },
      "ocr-device-mcp": {
        "url": "http://127.0.0.1:8104/mcp",
        "toolTimeout": 90
      }
    }
  }
}
```

---

## 这个配置你需要改的地方

你真正要改的只有这几项：

### 1）`YOUR_QWEN_MODEL_NAME`

替换成你当前本地服务真正暴露的模型名。
如果你本地 OpenAI-compatible 接口把它暴露成 `qwen3.5-9bq4`，就直接填这个；如果暴露成别的名字，按实际名字填。

### 2）`YOUR_PROVIDER_NAME`

替换成你当前 nanobot build 已支持的 provider 名称。
如果你现在是通过本地 OpenAI-compatible 方式暴露模型，这里通常会对应一个 OpenAI-compatible 或自定义 provider 名称；但这个名字要以你当前 nanobot 版本实际可用的 provider registry 为准。最近版本确实新增了更多 provider 和 OpenAI-compatible 支持。([github.com](https://github.com/HKUDS/nanobot/releases?utm_source=chatgpt.com))

### 3）`YOUR_TELEGRAM_USER_ID`

替换成你自己的 Telegram 用户 ID。
nanobot 安全策略页明确建议在生产环境里显式配置 `allowFrom`，并且新版本默认空 `allowFrom` 倾向于拒绝访问，而不是放开。([github.com](https://github.com/HKUDS/nanobot/security/policy?utm_source=chatgpt.com))

### 4）4 个 MCP 地址

这 4 个地址对应你后端实际启动的 MCP server。
README 明确说明 `mcpServers` 可以直接用 HTTP 远程 endpoint，也可以用本地进程方式；你这里更适合 HTTP，因为 vision/memory/state/ocr 这几块本来就是 sidecar。([github.com](https://github.com/HKUDS/nanobot/blob/main/README.md?utm_source=chatgpt.com))

---

## 如果你想改成本地进程式 MCP

如果你更想让 nanobot 直接拉起本地 MCP 进程，可以把某个 server 改成下面这种：

```text id="mpg25m"
{
  "tools": {
    "mcpServers": {
      "state-policy-mcp": {
        "command": "python",
        "args": ["-m", "src.mcp_server.state_policy_server"],
        "toolTimeout": 60
      }
    }
  }
}
```

这也是 nanobot README 里明确支持的 stdio 模式。([github.com](https://github.com/HKUDS/nanobot/blob/main/README.md?utm_source=chatgpt.com))

---

# 二、7 个 `SKILL.md` 初版内容

下面我按目录逐个给你。
你直接在仓库里建：

* `skills/scene_query/SKILL.md`
* `skills/history_query/SKILL.md`
* `skills/last_seen/SKILL.md`
* `skills/object_state/SKILL.md`
* `skills/zone_state/SKILL.md`
* `skills/ocr_query/SKILL.md`
* `skills/device_status/SKILL.md`

---

## 1）`skills/scene_query/SKILL.md`

```text id="k7mbvu"
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
```

---

## 2）`skills/history_query/SKILL.md`

```text id="k0q8vy"
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
```

---

## 3）`skills/last_seen/SKILL.md`

```text id="8l5db4"
---
name: last_seen
description: Answer questions about the last observed location or time of an object.
metadata: {"openclaw":{"always":true}}
---

# last_seen

## Purpose
Use this skill when the user asks where or when an object was last seen.

## Use this skill for
- 杯子最后一次在哪里看到
- 快递最后一次是什么时候出现
- 猫最后一次在哪个区域出现
- 最后一次看到钥匙是什么时候

## Do not use this skill for
- 当前状态推定
- 区域占用状态
- 当前画面描述
- OCR

## Preferred tools
- last_seen_object
- evaluate_staleness

## Allowed tools
- last_seen_object
- evaluate_staleness

## Allowed resources
- resource://memory/observations
- resource://memory/object_states
- resource://policy/freshness

## Freshness policy
- Always mention the timestamp of the last sighting.
- If the last sighting is stale, say it clearly.
- Do not convert last_seen into present-state certainty unless the user explicitly asks.

## Fallback rules
1. If no last_seen record exists, say the object has no recorded sighting.
2. If the record is stale, mention that it may no longer reflect the current situation.
3. If the user then asks for live confirmation, the system may switch to snapshot flow.

## Execution steps
1. Identify the target object.
2. Call `last_seen_object`.
3. Call `evaluate_staleness` on the result if freshness metadata is not obvious.
4. Return location, time, and confidence.
5. Do not overstate certainty beyond the recorded sighting.

## Output requirements
Return:
- object name
- last seen time
- camera / zone
- stale or non-stale indication
- confidence / source layer if available

## Style guidance
- Be factual.
- Separate "last seen" from "currently present".
```

---

## 4）`skills/object_state/SKILL.md`

```text id="2kni5n"
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
```

---

## 5）`skills/zone_state/SKILL.md`

```text id="cbapm6"
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
```

---

## 6）`skills/ocr_query/SKILL.md`

```text id="5but6m"
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
```

---

## 7）`skills/device_status/SKILL.md`

```text id="cjlwmv"
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
```

---

# 三、我建议你放进仓库后的实际落位

你现在可以直接这样落：

```text id="m84ikm"
config/nanobot.config.json

skills/
├─ scene_query/
│  └─ SKILL.md
├─ history_query/
│  └─ SKILL.md
├─ last_seen/
│  └─ SKILL.md
├─ object_state/
│  └─ SKILL.md
├─ zone_state/
│  └─ SKILL.md
├─ ocr_query/
│  └─ SKILL.md
└─ device_status/
   └─ SKILL.md
```

---

# 四、你现在最适合怎么用这两份

建议顺序是：

1. 先把 `config/nanobot.config.json` 放到 `config/`
2. 把 7 个 Skill 放进 `skills/`
3. 然后把我前面给你的 **Prompt 11（nanobot 集成）** 和 **Prompt 10（Skill 层）** 分别喂给 Codex
4. 让 Codex 去补：

   * `gateway/nanobot_workspace/`
   * `docs/DEPLOYMENT.md`
   * `skill_registry.py`（如果你要）
   * MCP 对接说明

---

# 五、我对这两份内容的最后提醒

这两份现在已经够你启动开发，但有两个地方你要记住：

**第一，provider 名称和本地 Qwen 接法，要以你当前 nanobot build 为准。**
因为 nanobot 最近 provider registry 和 OpenAI-compatible 支持还在快速演进，发布说明里也明确说最近一个大版本新增了更多 provider 和兼容性增强。([github.com](https://github.com/HKUDS/nanobot/releases?utm_source=chatgpt.com))

**第二，Skill 正文可以直接用，frontmatter 键如果你本地解析器有差异，可以微调。**
因为 OpenClaw 的 Skill 约定是成熟的，而 nanobot 这边更适合作为兼容风格来用；正文里的“何时调用哪个工具、何时 fallback、输出要求是什么”这些内容本身不需要大改。([docs.openclaw.ai](https://docs.openclaw.ai/zh-CN/tools/skills?utm_source=chatgpt.com))

如果你要，我下一条可以继续直接给你两份最实用的东西：

1. **`docs/DEPLOYMENT.md` 初版**
2. **`scripts/start_gateway.sh`、`start_backend.sh`、`start_edge.sh`、`smoke_test.sh` 四个脚本模板**




可以，下面我把你要的两部分一次性发全：

1. **`docs/DEPLOYMENT.md` 初版**
2. **4 个脚本模板**

   * `scripts/start_gateway.sh`
   * `scripts/start_backend.sh`
   * `scripts/start_edge.sh`
   * `scripts/smoke_test.sh`

先说明一下这套内容为什么这样组织：
nanobot 现在公开支持通过 `--config` 启动独立实例，并且可以为不同实例使用独立 workspace；同时它支持 Telegram channel、`allowFrom`、以及通过 `tools.mcpServers` 挂接本地或远程 MCP server。Telegram Bot API 侧，`getUpdates` 和 `setWebhook` 是互斥的两种收消息方式，未消费的更新最多保留 24 小时；而 MCP 规范里，tools/resources/prompts 本来就是标准暴露面。也就是说，你现在这套 `Telegram + nanobot + MCP + sidecar services` 的部署方式是顺的。([github.com](https://github.com/HKUDS/nanobot/blob/main/README.md?utm_source=chatgpt.com)) ([core.telegram.org](https://core.telegram.org/bots/api?utm_source=chatgpt.com)) ([modelcontextprotocol.io](https://modelcontextprotocol.io/specification/2025-03-26?utm_source=chatgpt.com))

另外，Qwen 的官方工具调用和结构化输出文档都明确说明：应用应把工具清单给模型，模型决定是否调用工具，应用执行后再把结果回灌模型；如果需要稳定 JSON，应使用结构化输出模式。因此部署文档里我会明确把 **Qwen3.5 定位为模型层**，把 **OCR / state / device** 这类能力部署为独立服务，而不是塞进模型侧。([help.aliyun.com](https://help.aliyun.com/zh/model-studio/qwen-function-calling?utm_source=chatgpt.com)) ([help.aliyun.com](https://help.aliyun.com/zh/model-studio/qwen-structured-output?utm_source=chatgpt.com))

---

# 一、`docs/DEPLOYMENT.md` 初版

```text id="d29sfe"
# DEPLOYMENT.md

## 1. 文档目的

本文档用于说明 Vision Butler v5 的正式部署方式。

本项目的正式部署组成如下：
- Telegram Bot：唯一用户入口
- nanobot：唯一主控宿主
- Qwen3.5 多模态模型：理解、工具决策、简单 OCR
- Backend Sidecar Services：memory / state / policy / security / device / OCR
- MCP Servers：把正式能力暴露给 nanobot
- SQLite + FTS5：正式单机数据层
- RK3566 Edge Device：边缘采集、轻量检测、事件压缩、心跳与媒体回传

---

## 2. 正式部署原则

1. Telegram 是正式入口，不是测试入口。
2. nanobot 是正式宿主，但不是业务真相层。
3. 所有正式业务能力优先通过 MCP 暴露给 nanobot。
4. 后端服务是状态、记忆、OCR、设备与权限的事实层。
5. RK3566 前端只负责事件感知与媒体回传。
6. 当前阶段正式数据库采用 SQLite + FTS5。
7. 正式与开发环境必须隔离。

---

## 3. 推荐部署拓扑

### 3.1 x86 主机运行内容
- nanobot
- backend API
- MCP servers
- SQLite 数据库
- media storage
- logs / audit logs

### 3.2 RK3566 前端运行内容
- camera capture
- detector / tracker
- event compressor
- ring buffer cache
- device API
- heartbeat sender

### 3.3 Telegram 入口
- Telegram Bot API
- nanobot Telegram channel
- allowFrom 只允许正式用户

---

## 4. 目录约定

推荐目录：

- config/
- docs/
- gateway/
- edge_device/
- src/
- skills/
- scripts/
- tests/

关键路径：
- config/nanobot.config.json
- gateway/nanobot_workspace/
- schema.sql
- migrations/
- media/
- logs/

---

## 5. 环境变量建议

建议使用环境变量提供敏感配置，不要把真实密钥写死在仓库。

### 主机侧建议环境变量
- TELEGRAM_BOT_TOKEN
- TELEGRAM_ALLOWED_USER_ID
- QWEN_PROVIDER_NAME
- QWEN_MODEL_NAME
- QWEN_API_BASE
- QWEN_API_KEY
- SQLITE_DB_PATH
- MEDIA_ROOT
- MCP_VISION_URL
- MCP_MEMORY_URL
- MCP_STATE_POLICY_URL
- MCP_OCR_DEVICE_URL
- BACKEND_HOST
- BACKEND_PORT

### 前端侧建议环境变量
- EDGE_DEVICE_ID
- EDGE_CAMERA_ID
- EDGE_API_KEY
- EDGE_BACKEND_BASE
- EDGE_SNAPSHOT_DIR
- EDGE_CLIP_DIR
- EDGE_MODEL_NAME

---

## 6. 正式部署顺序

建议按以下顺序启动：

1. 初始化数据库
2. 启动 backend API
3. 启动 MCP servers
4. 启动 nanobot gateway
5. 启动 RK3566 edge service
6. 执行 smoke test
7. 用 Telegram 做首次验证

---

## 7. 数据库初始化

第一次部署前执行：

- 初始化 SQLite 数据库
- 执行 schema.sql 或依次执行 migrations/sql/*
- 检查主表、索引、FTS、视图是否存在

建议最少检查：
- users
- devices
- observations
- events
- object_states
- zone_states
- media_items
- audit_logs
- telegram_updates
- notification_rules
- ocr_results
- observations_fts
- events_fts
- ocr_results_fts

---

## 8. backend API 启动要求

backend API 负责：
- /healthz
- /memory/*
- /policy/*
- /device/*
- /ocr/*
- /device/heartbeat
- /device/ingest/event

启动前确认：
- 数据库路径有效
- 配置文件完整
- media 根目录存在
- audit / log 目录可写

---

## 9. MCP servers 启动要求

正式 MCP 能力至少包括：

### vision-mcp
- take_snapshot
- get_recent_clip
- describe_scene

### memory-mcp
- query_recent_events
- last_seen_object

### state-policy-mcp
- get_object_state
- get_zone_state
- get_world_state
- evaluate_staleness

### ocr-device-mcp
- ocr_quick_read
- ocr_extract_fields
- device_status
- refresh_object_state
- refresh_zone_state

部署时要确认：
- 每个 MCP server 都有独立端口或独立进程
- nanobot.config.json 中的 mcpServers URL 正确
- health endpoint（如果有）可访问
- tool timeout 合理

---

## 10. nanobot 启动要求

正式 nanobot 应满足：
- 使用单独 config 文件启动
- 使用独立 workspace
- Telegram channel enabled
- allowFrom 生效
- 正确挂载 MCP servers
- 使用正式 Qwen3.5 模型配置

正式环境应至少准备两个实例：
- prod：正式 bot
- dev：测试 bot

正式与测试实例必须隔离：
- 独立 Telegram token
- 独立 workspace
- 独立数据库或独立 DB 文件
- 独立 media 目录
- 独立 logs

---

## 11. RK3566 前端启动要求

前端启动前确认：
- 摄像头可用
- 本地缓存目录存在
- device_id / camera_id / api_key 已配置
- 能访问 backend API
- heartbeat 间隔合理

前端必须支持：
- 定时 heartbeat
- 接收 snapshot / clip 命令
- 输出统一 event envelope
- 保存最近 snapshot / clip
- 失败时给出明确错误日志

---

## 12. Telegram 正式上线前检查

上线前必须检查：

1. Bot token 是否正确
2. allowFrom 是否只包含允许用户
3. nanobot 实例是否连到正式 workspace
4. telegram_updates 去重逻辑是否可用
5. 长消息分片是否可用
6. sendChatAction 是否可用
7. 图片消息是否能进入 OCR / scene query 流程
8. 命令入口是否可用：
   - /snapshot
   - /clip
   - /lastseen
   - /state
   - /ocr
   - /device
   - /help

---

## 13. 正式 smoke test

正式 smoke test 至少应验证：

1. backend /healthz 正常
2. 数据库主表存在
3. 至少一个 MCP tool 可调用
4. nanobot 能启动
5. Telegram 文本消息可收到并处理
6. 设备状态查询可用
7. snapshot 命令可用
8. OCR quick read 可用

---

## 14. 日志与审计

正式部署必须保留以下日志：
- backend service logs
- nanobot logs
- edge device logs
- audit_logs 数据表
- telegram_updates 状态表

所有敏感行为必须进入审计：
- 用户访问
- 工具调用
- 权限拒绝
- 设备命令
- 媒体读取
- OCR 结构化提取

---

## 15. 当前可运行范围与 stub 说明

当前版本允许以下部分以 adapter / stub 方式先运行：
- 真实 RKNN 检测器
- 真实 OCR provider
- 真实 MCP server 框架适配
- 真实 edge 设备命令执行

但以下部分应当是真正存在的：
- 仓库结构
- 数据库 schema
- 路由与服务骨架
- nanobot 配置
- Skills
- 基础测试
- 启动脚本
- smoke test

---

## 16. 首次启动建议顺序

1. 配置环境变量
2. 运行 scripts/init_db.sh
3. 运行 scripts/start_backend.sh
4. 运行 scripts/start_gateway.sh
5. 运行 scripts/start_edge.sh
6. 运行 scripts/smoke_test.sh
7. 用 Telegram 发送 /help
8. 再测试 /device、/snapshot、/ocr

---

## 17. 故障排查建议

### backend 无法启动
检查：
- SQLite 路径
- 配置文件
- 端口占用
- schema 是否已初始化

### nanobot 无法调用工具
检查：
- mcpServers URL
- tool timeout
- MCP 服务是否已启动
- workspace 是否正确

### Telegram 无响应
检查：
- Bot token
- allowFrom
- update 去重逻辑
- polling / webhook 是否冲突

### edge 无法回传事件
检查：
- device_id / api_key
- backend 地址
- 本地缓存目录
- heartbeat 是否成功

---

## 18. 正式部署完成定义

只有同时满足以下条件，才算部署完成：
- 数据库初始化成功
- backend 服务可用
- MCP tools 可调用
- nanobot 正常启动
- Telegram 问答可用
- 设备状态查询可用
- snapshot 可用
- OCR 可用
- 审计可记录
- smoke test 通过
```

---

# 二、脚本模板

下面 4 个脚本我都按**可直接改造使用**的方式写。
默认假设你用的是 Linux/macOS shell，后端是 Python，nanobot 通过 `--config` 启动实例；这个 `--config` 用法和 workspace 独立实例是 nanobot README 明确支持的。([github.com](https://github.com/HKUDS/nanobot/blob/main/README.md?utm_source=chatgpt.com))

---

## `scripts/start_gateway.sh`

```text id="doofy5"
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_FILE="${ROOT_DIR}/config/nanobot.config.json"
WORKSPACE_DIR="${ROOT_DIR}/gateway/nanobot_workspace"

: "${TELEGRAM_BOT_TOKEN:=YOUR_TELEGRAM_BOT_TOKEN}"
: "${TELEGRAM_ALLOWED_USER_ID:=YOUR_TELEGRAM_USER_ID}"
: "${QWEN_PROVIDER_NAME:=YOUR_PROVIDER_NAME}"
: "${QWEN_MODEL_NAME:=YOUR_QWEN_MODEL_NAME}"
: "${QWEN_API_BASE:=http://127.0.0.1:8000/v1}"
: "${QWEN_API_KEY:=DUMMY_OR_REAL_API_KEY}"

mkdir -p "${WORKSPACE_DIR}"

echo "[INFO] Starting nanobot gateway"
echo "[INFO] Root: ${ROOT_DIR}"
echo "[INFO] Config: ${CONFIG_FILE}"
echo "[INFO] Workspace: ${WORKSPACE_DIR}"

if [[ ! -f "${CONFIG_FILE}" ]]; then
  echo "[ERROR] Missing config file: ${CONFIG_FILE}"
  exit 1
fi

# 这里默认你已经安装了 nanobot CLI 或可执行入口
# 如果你本地命令不是 nanobot，请改成实际可执行命令
exec nanobot \
  --config "${CONFIG_FILE}" \
  --workspace "${WORKSPACE_DIR}"
```

---

## `scripts/start_backend.sh`

```text id="ygvm6k"
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

: "${BACKEND_HOST:=0.0.0.0}"
: "${BACKEND_PORT:=8100}"
: "${SQLITE_DB_PATH:=${ROOT_DIR}/data/vision_butler.db}"
: "${MEDIA_ROOT:=${ROOT_DIR}/media}"
: "${PYTHON_BIN:=python}"

mkdir -p "${ROOT_DIR}/data"
mkdir -p "${MEDIA_ROOT}"
mkdir -p "${ROOT_DIR}/logs"

export SQLITE_DB_PATH
export MEDIA_ROOT

echo "[INFO] Starting backend API"
echo "[INFO] DB: ${SQLITE_DB_PATH}"
echo "[INFO] Media root: ${MEDIA_ROOT}"
echo "[INFO] Host: ${BACKEND_HOST}"
echo "[INFO] Port: ${BACKEND_PORT}"

# 如果你最终采用 uvicorn + FastAPI
exec "${PYTHON_BIN}" -m uvicorn src.app:app \
  --host "${BACKEND_HOST}" \
  --port "${BACKEND_PORT}" \
  --reload
```

> 如果你正式环境不想 `--reload`，把这一项删掉即可。

---

## `scripts/start_edge.sh`

```text id="q5qjcj"
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

: "${EDGE_DEVICE_ID:=rk3566-01}"
: "${EDGE_CAMERA_ID:=camera-door-01}"
: "${EDGE_API_KEY:=CHANGE_ME}"
: "${EDGE_BACKEND_BASE:=http://127.0.0.1:8100}"
: "${EDGE_SNAPSHOT_DIR:=${ROOT_DIR}/edge_runtime/snapshots}"
: "${EDGE_CLIP_DIR:=${ROOT_DIR}/edge_runtime/clips}"
: "${EDGE_MODEL_NAME:=yolov6n}"
: "${PYTHON_BIN:=python}"

mkdir -p "${EDGE_SNAPSHOT_DIR}"
mkdir -p "${EDGE_CLIP_DIR}"
mkdir -p "${ROOT_DIR}/logs"

export EDGE_DEVICE_ID
export EDGE_CAMERA_ID
export EDGE_API_KEY
export EDGE_BACKEND_BASE
export EDGE_SNAPSHOT_DIR
export EDGE_CLIP_DIR
export EDGE_MODEL_NAME

echo "[INFO] Starting edge service"
echo "[INFO] Device: ${EDGE_DEVICE_ID}"
echo "[INFO] Camera: ${EDGE_CAMERA_ID}"
echo "[INFO] Backend: ${EDGE_BACKEND_BASE}"
echo "[INFO] Snapshot dir: ${EDGE_SNAPSHOT_DIR}"
echo "[INFO] Clip dir: ${EDGE_CLIP_DIR}"

# 这里默认 edge 入口为 edge_device.api.server
# 你后续可以让 Codex 把真实入口补到这个路径
exec "${PYTHON_BIN}" -m edge_device.api.server
```

---

## `scripts/smoke_test.sh`

```text id="3g10k7"
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

: "${BACKEND_BASE:=http://127.0.0.1:8100}"
: "${SQLITE_DB_PATH:=${ROOT_DIR}/data/vision_butler.db}"
: "${SQLITE_BIN:=sqlite3}"
: "${CURL_BIN:=curl}"

echo "[INFO] Running smoke tests"

if [[ ! -f "${SQLITE_DB_PATH}" ]]; then
  echo "[ERROR] Database file not found: ${SQLITE_DB_PATH}"
  exit 1
fi

echo "[INFO] 1/5 Check tables"
"${SQLITE_BIN}" "${SQLITE_DB_PATH}" "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;" | grep -q "observations"
"${SQLITE_BIN}" "${SQLITE_DB_PATH}" "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;" | grep -q "events"
"${SQLITE_BIN}" "${SQLITE_DB_PATH}" "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;" | grep -q "object_states"
"${SQLITE_BIN}" "${SQLITE_DB_PATH}" "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;" | grep -q "zone_states"

echo "[INFO] 2/5 Check FTS tables"
"${SQLITE_BIN}" "${SQLITE_DB_PATH}" "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_fts';" | grep -q "observations_fts"
"${SQLITE_BIN}" "${SQLITE_DB_PATH}" "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_fts';" | grep -q "events_fts"

echo "[INFO] 3/5 Check backend health"
"${CURL_BIN}" -fsS "${BACKEND_BASE}/healthz" >/dev/null

echo "[INFO] 4/5 Check state route exists"
"${CURL_BIN}" -fsS "${BACKEND_BASE}/memory/world-state" >/dev/null || true

echo "[INFO] 5/5 Check device status route exists"
"${CURL_BIN}" -fsS "${BACKEND_BASE}/device/status?device_id=test-device" >/dev/null || true

echo "[INFO] Smoke tests passed"
```

---

# 三、建议你再补一个 `scripts/init_db.sh`

虽然你这次只点名要 4 个脚本，但从启动链路看，`init_db.sh` 是必需的。
我顺手也给你一份，方便你直接放进去。

```text id="8m3pr8"
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

: "${SQLITE_DB_PATH:=${ROOT_DIR}/data/vision_butler.db}"
: "${SQLITE_BIN:=sqlite3}"
: "${SCHEMA_FILE:=${ROOT_DIR}/schema.sql}"

mkdir -p "${ROOT_DIR}/data"

if [[ ! -f "${SCHEMA_FILE}" ]]; then
  echo "[ERROR] schema.sql not found: ${SCHEMA_FILE}"
  exit 1
fi

echo "[INFO] Initializing database"
echo "[INFO] DB: ${SQLITE_DB_PATH}"
echo "[INFO] Schema: ${SCHEMA_FILE}"

"${SQLITE_BIN}" "${SQLITE_DB_PATH}" < "${SCHEMA_FILE}"

echo "[INFO] Database initialized"
```

---

# 四、你现在可以怎么落仓库

直接按这个结构放：

```text id="rvl62e"
docs/DEPLOYMENT.md

scripts/start_gateway.sh
scripts/start_backend.sh
scripts/start_edge.sh
scripts/smoke_test.sh
scripts/init_db.sh
```

然后给这些脚本执行权限：

```text id="qlbq2a"
chmod +x scripts/start_gateway.sh
chmod +x scripts/start_backend.sh
chmod +x scripts/start_edge.sh
chmod +x scripts/smoke_test.sh
chmod +x scripts/init_db.sh
```

---

# 五、下一步最推荐的实际动作

你现在手里的材料已经足够正式开工了。
最推荐的顺序是：

1. 把 `AGENTS.md`、`TASKS.md` 放进仓库
2. 把 `schema.sql`、`migrations/README.md` 放进去
3. 把 `config/nanobot.config.json` 放进去
4. 把 7 个 Skill 放进 `skills/`
5. 把这次的 `DEPLOYMENT.md` 和 `scripts/*.sh` 放进去
6. 然后把 **Prompt 1** 和 **Prompt 2** 先喂给 Codex

这样你就不是“从零开工”，而是已经有了：

* 计划书
* 图
* 表
* SQL
* 迁移
* 配置
* Skill
* 启动脚本
* 任务板
* Codex prompts

如果你要，我下一条可以继续给你最后两类特别实用的成品：

1. **`README.md` 初版**
2. **`docs/ARCHITECTURE.md` 初版**

这两份一补，你的“文档侧启动包”就基本闭环了。


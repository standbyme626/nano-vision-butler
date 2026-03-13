# Snapshot Contract (T13D)

本文定义 edge 侧 snapshot 的最小正式契约，作为 T13D 验收基线。

## 1. 目标

- snapshot 必须是可被标准图像工具读取的真实 JPEG
- snapshot 尺寸必须与采集帧一致
- snapshot URI 必须可回传后端并在 `observations.snapshot_uri` 落库查询

## 2. 生成位置

- 代码入口：`edge_device/api/server.py::_store_snapshot`
- 文件后缀：`.jpg`
- URI 形态：`file:///absolute/path/to/<camera>_<frame_id>.jpg`

## 3. 快照元数据字段

`take_snapshot` / `run_once` 相关字段：

- `snapshot_uri`
- `snapshot_path`
- `captured_at`
- `width`
- `height`

其中 `width/height` 来自当前 `CapturedFrame`，必须与 JPEG 实际尺寸一致。

## 4. 最小验证命令

```bash
python3 -m edge_device.api.server take-snapshot --trace-id t13d-check
```

从输出里取 `data.snapshot_uri` 后验证：

```bash
python3 - <<'PY'
from pathlib import Path
from urllib.parse import urlparse
from PIL import Image

uri = "file:///replace/with/snapshot.jpg"
path = Path(urlparse(uri).path)
with Image.open(path) as img:
    print("format=", img.format, "size=", img.size)
PY
```

预期：
- `format= JPEG`
- `size=(<frame_width>, <frame_height>)`

## 5. 后端落库校验

当 edge event 上报含 `snapshot_uri` 时，后端 `POST /device/ingest/event` 应可保存：

- `observations.snapshot_uri = payload.snapshot_uri`
- 可通过 `WHERE snapshot_uri = ?` 定位记录

## 6. 版本说明

- 当前协议版本：`edge.event.v1`
- 本文适用任务：`T13D`

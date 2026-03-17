# Task 2: Implementer — narrative.py

实现 spine/narrative.py，让 tests/test_narrative.py 的所有测试通过。

## Python 版本
Python 3.9。不要用 `X | None`，用 `Optional[X]`。不要用 match/case。

## 铁律
- 严禁修改测试文件
- 严格遵循接口签名

## 需要实现的接口
```python
def append_narrative(narratives_dir: str, node_id: str,
                      timestamp: str, event_type: str,
                      content: str, mentions: Optional[list] = None) -> bool:
    """追加叙事到 narratives/{node_id}.md。
    格式: ## {timestamp} [{event_type}]\n{content}\n
    如果有 mentions: 在 content 后加 Mentions: node-1, node-2
    返回 True 成功，False 失败（不抛异常）。
    自动创建目录和文件。"""

def read_narrative(narratives_dir: str, node_id: str,
                    last_n_entries: Optional[int] = None,
                    since_days: Optional[int] = None) -> str:
    """读取叙事。
    - 无参数: 返回全文
    - last_n_entries: 返回最后 N 条（按 ## 分割）
    - since_days: 返回最近 N 天的条目
    - 文件不存在: 返回空字符串"""

def read_compressed(narratives_dir: str, node_id: str) -> Optional[str]:
    """读取 {node_id}.compressed.md。不存在返回 None。"""

def write_compressed(narratives_dir: str, node_id: str, content: str) -> None:
    """写入压缩摘要。可覆盖（这是派生物，不是叙事）。"""

def write_repair_event(narratives_dir: str, node_id: str,
                        original_event: dict, error: str) -> None:
    """写入修复事件到 {node_id}.repair.md。
    格式包含原始事件 JSON 和错误信息。
    自动创建目录。"""
```

## 关键规则
- 叙事文件 (.md) 是 append-only，只追加不覆盖
- 压缩文件 (.compressed.md) 可覆盖
- 修复文件 (.repair.md) 追加
- 所有写操作自动创建不存在的目录
- append 失败时返回 False，捕获所有异常

## 验证
完成后运行: `cd /Users/jeff/.openclaw/workspace/fpms && python3 -m pytest tests/test_narrative.py -v`
确保全部通过。

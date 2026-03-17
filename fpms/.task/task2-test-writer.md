# Task 2: Test Writer — narrative.py

你是测试工程师。为 narrative.py 编写测试。

## Python 版本
Python 3.9。不要用 `X | None`，用 `Optional[X]`。不要用 match/case。

## 接口签名
```python
def append_narrative(narratives_dir: str, node_id: str,
                      timestamp: str, event_type: str,
                      content: str, mentions: Optional[list] = None) -> bool:
    """追加叙事到 narratives/{node_id}.md。
    格式: ## {timestamp} [{event_type}]\n{content}
    返回是否成功。失败不抛异常，返回 False。"""

def read_narrative(narratives_dir: str, node_id: str,
                    last_n_entries: Optional[int] = None,
                    since_days: Optional[int] = None) -> str:
    """读取叙事。支持按条数或天数截取。"""

def read_compressed(narratives_dir: str, node_id: str) -> Optional[str]:
    """读取 {node_id}.compressed.md。不存在返回 None。"""

def write_compressed(narratives_dir: str, node_id: str, content: str) -> None:
    """写入压缩摘要。"""

def write_repair_event(narratives_dir: str, node_id: str,
                        original_event: dict, error: str) -> None:
    """写入修复事件记录。"""
```

## PRD 规则 (FR-2)
- 叙事文件是 append-only，禁止覆盖/删除已有内容
- 每条叙事格式: `## {timestamp} [{event_type}]\n{content}\n`
- mentions 记录引用的其他 node_id
- 写入失败返回 False，不抛异常
- repair_event 记录原始事件和错误信息

## 测试要点
- append_narrative 追加格式正确
- append_narrative 多次追加不覆盖（append-only 验证）
- append_narrative 含 mentions 的格式
- append_narrative 文件不存在时自动创建目录和文件
- append_narrative 返回 True/False
- read_narrative 全文读取
- read_narrative last_n_entries=2 截取最后 2 条
- read_narrative since_days=3 截取近 3 天
- read_narrative 空文件返回空字符串
- read_compressed 存在时返回内容
- read_compressed 不存在返回 None
- write_compressed 正常写入
- write_compressed 覆盖已有压缩（压缩文件可覆盖，不是叙事）
- write_repair_event 写入包含原始事件和错误
- write_repair_event 目标目录不存在时创建

## 约束
- 只输出 tests/test_narrative.py
- 不写任何实现代码
- 使用 pytest + tempfile

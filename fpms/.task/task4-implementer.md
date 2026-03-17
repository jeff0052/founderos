# Task 4: Implementer — validator.py

实现 spine/validator.py，让 tests/test_validator.py 的所有测试通过。

## Python 版本
Python 3.9。不要用 `X | None`，用 `Optional[X]`。不要用 match/case。

## 铁律
- 严禁修改测试文件
- 严格遵循接口签名
- store.py 已实现，可以 import 使用

## 已有代码
- spine/store.py: Store class（CRUD + 事务 + graph queries）
- spine/models.py: Node, Edge dataclasses

## 接口
```python
class ValidationError(Exception):
    def __init__(self, code: str, message: str, suggestion: str = ""):
        self.code = code; self.message = message; self.suggestion = suggestion

def validate_status_transition(current, target, node, children): ...
def validate_dag_safety(store, source_id, target_id, edge_type): ...
def validate_xor_constraint(is_root, parent_id): ...
def validate_active_domain(node): ...
def validate_attach(store, node_id, new_parent_id): ...
def validate_dependency(store, source_id, target_id): ...
```

## 状态机规则
合法迁移:
- inbox → active, waiting, dropped
- active → waiting, done, dropped
- waiting → active, done, dropped
- done → active（需 reason）
- dropped → inbox（需 reason）

前置条件:
- inbox→active/waiting: 需要 summary 且 (parent_id OR is_root)
- →done: 所有子节点必须终态
- →dropped: 允许，不 raise（活跃子节点 warning 由调用方处理）

## DAG 检测
使用 WITH RECURSIVE CTE 在 SQLite 层检测:
```sql
WITH RECURSIVE reachable(id) AS (
    SELECT ? -- target_id
    UNION
    SELECT e.target_id FROM edges e
    JOIN reachable r ON e.source_id = r.id
    WHERE e.edge_type IN ('parent', 'depends_on')
)
SELECT 1 FROM reachable WHERE id = ? -- source_id
```
如果 source_id 可从 target_id 到达 → 添加 source→target 边会形成环 → 拒绝。

对于跨维度死锁: 如果 source 是 target 的后代（通过 parent 链），则 source depends_on target = 死锁。
用 store.get_ancestors(source_id) 检查 target_id 是否在祖先中。

## Actionable Errors
每个 ValidationError 必须包含:
- code: 如 "MISSING_SUMMARY", "CYCLE_DETECTED", "XOR_VIOLATION"
- message: 人可读描述
- suggestion: 修复建议，如 "请先调用 update_field(node_id=xxx, field='summary', value='...') 补充"

## 验证
完成后运行: `cd /Users/jeff/.openclaw/workspace/fpms && python3 -m pytest tests/test_validator.py -v`

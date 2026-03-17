# Task 4: Test Writer — validator.py

你是测试工程师。为 validator.py 编写测试。

## Python 版本
Python 3.9。不要用 `X | None`，用 `Optional[X]`。不要用 match/case。

## 已有代码
- spine/schema.py, spine/models.py, spine/store.py 将已实现
- 测试中需要 store fixture 来创建节点和边

## 接口签名

```python
class ValidationError(Exception):
    def __init__(self, code: str, message: str, suggestion: str = ""):
        self.code = code
        self.message = message
        self.suggestion = suggestion

def validate_status_transition(current: str, target: str, node: Node,
                                children: list) -> None:
    """校验状态迁移。不合法 raise ValidationError。"""

def validate_dag_safety(store: Store, source_id: str, target_id: str,
                         edge_type: str) -> None:
    """统一 DAG 环路检测（WITH RECURSIVE CTE）。"""

def validate_xor_constraint(is_root: bool, parent_id: Optional[str]) -> None:
    """is_root 和 parent_id 互斥。"""

def validate_active_domain(node: Node) -> None:
    """目标非归档。"""

def validate_attach(store: Store, node_id: str, new_parent_id: str) -> None:
    """综合: 活跃域 + DAG + XOR。"""

def validate_dependency(store: Store, source_id: str, target_id: str) -> None:
    """综合: 活跃域 + DAG + 不能自依赖。"""
```

## 状态机规则 (FR-5.1)
```
inbox → active, waiting, dropped
active → waiting, done, dropped
waiting → active, done, dropped
done → active (needs reason)
dropped → inbox (needs reason)
```

前置条件:
- inbox→active/waiting: 需要 summary + (parent_id OR is_root)
- →done: 所有子节点必须终态 (done/dropped)
- →dropped: 允许但活跃子节点产生 warning
- done→active / dropped→inbox: 需要 reason（通过外部传入，validator 检查 node 状态）

## DAG 规则
- parent + depends_on 合并为统一有向图
- 任何方向的环路都拒绝
- 子节点 depends_on 祖先 = 跨维度死锁，拒绝
- 自依赖拒绝

## 测试要点

### validate_status_transition
- 所有合法迁移通过（9种）
- 所有非法迁移拒绝（7种: inbox→done, done→waiting, done→dropped, done→inbox, dropped→active, dropped→waiting, dropped→done）
- inbox→active 缺 summary → 拒绝 + actionable suggestion
- inbox→active 缺 parent_id 且非 root → 拒绝
- →done 有活跃子节点 → 拒绝 + 列出子节点
- →done 所有子节点终态 → 通过
- →dropped 有活跃子节点 → 通过（不 raise，但 warning 由调用方处理）

### validate_dag_safety（需要 store fixture）
- parent 环 A→B→A → 拒绝
- depends_on 环 → 拒绝
- 跨维度: child depends_on ancestor → 拒绝
- 正常无环 → 通过

### validate_xor_constraint
- True + None → OK
- False + "id" → OK
- False + None → OK
- True + "id" → 拒绝

### validate_active_domain
- archived_at 有值 → 拒绝
- archived_at=None → OK

### validate_attach / validate_dependency
- 正常 → OK
- 目标已归档 → 拒绝
- 会造成环 → 拒绝
- 自依赖 → 拒绝

### Actionable Errors
- 每个 ValidationError 都有非空 code
- 缺 summary 的错误包含 "update_field" 或 "summary" 建议

## conftest.py 需要的 fixture
```python
@pytest.fixture
def store(tmp_path):
    db_path = str(tmp_path / "test.db")
    events_path = str(tmp_path / "events.jsonl")
    from spine.schema import init_db
    from spine.store import Store
    init_db(db_path)
    return Store(db_path=db_path, events_path=events_path)
```

## 约束
- 只输出 tests/test_validator.py
- 不写实现代码
- 测试用到 store 时通过 fixture 创建真实 Store（不 mock）

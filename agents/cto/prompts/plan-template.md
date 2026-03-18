# Plan 文档格式标准

> **Protocol reference:** SUBAGENT-PROTOCOL.md  
> **Plan level selection:** §2.1 (risk level → plan level)  
> **Task grading:** §2.2 (decision table)

---

## 头部（所有级别必须）

```markdown
# [Feature Name] Implementation Plan

**Goal:** 一句话
**Architecture:** 2-3 句话
**Tech Stack:** 关键技术
**FPMS Task:** task-xxxx
**Module Spec:** 路径
**Risk Level:** L1 | L2 | L3 | L4
**Plan Level:** Lite | Standard | Heavy
**Complexity Budget:** 模块数上限 / 最大文件 LOC / 依赖深度上限
**Test Baseline:** `命令` → 预期结果
```

---

## Plan 分级

| Risk Level | Plan Level | 说明 |
|------------|------------|------|
| L1 | **Lite** | 单文件、边界清晰、无架构影响 |
| L2 | **Standard** | 跨文件但边界清晰 |
| L3 | **Heavy** | 跨模块、涉及架构决策 |
| L4 | **Heavy** | 支付核心、零容错 |

---

## Lite Plan（L1）

每个 task 只需：

```markdown
### Task N: [组件名]

**Files:**
- Modify: `exact/path/to/file.py:行号范围`
- Test: `tests/exact/path/to/test_file.py`

**Exclusions:** 不做什么
**Verify:** `pytest tests/test_file.py -v` → all pass
**Full suite:** `pytest tests/ -q` → no regressions
**Commit:** `fix(scope): description`
```

**不要求：** 内联完整实现/测试代码、每步 2-5 分钟拆分

---

## Standard Plan（L2）

每个 task 需要：

```markdown
### Task N: [组件名]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:行号范围`
- Test: `tests/exact/path/to/test_file.py`

**Exclusions:** 不做什么
**Constitution:** 适用铁律编号
**Depends on:** Task X（如有）

- [ ] Step 1: Write failing test
  ```python
  def test_xxx():
      # 测试骨架（不需要完整实现代码）
      result = function_under_test(input)
      assert result == expected
  ```

- [ ] Step 2: Run test, verify failure
  Run: `pytest tests/path/test_file.py::test_xxx -v`
  Expected: FAIL — ImportError / AssertionError

- [ ] Step 3: Implement (minimal)

- [ ] Step 4: Run test → PASS

- [ ] Step 5: Full suite → all pass

- [ ] Step 6: Commit: `feat(scope): description`
```

**要求：** 测试骨架、验证命令 + 预期输出、commit message  
**不要求：** 完整实现代码内联

---

## Heavy Plan（L3/L4）

每个 task 需要：

```markdown
### Task N: [组件名]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:行号范围`
- Test: `tests/exact/path/to/test_file.py`

**Exclusions:** 不做什么
**Constitution:** 适用铁律编号（逐条标注）
**Depends on:** Task X

- [ ] Step 1: Write failing test
  ```python
  # 完整测试代码
  def test_xxx():
      ...
  ```

- [ ] Step 2: Run test, verify failure
  Run: `pytest tests/path/test_file.py::test_xxx -v`
  Expected: FAIL with "具体错误信息"

- [ ] Step 3: Write minimal implementation
  ```python
  # 完整实现代码
  def xxx():
      ...
  ```

- [ ] Step 4: Run test, verify pass
  Run: `pytest tests/path/test_file.py::test_xxx -v`
  Expected: PASS

- [ ] Step 5: Run full suite, no regressions
  Run: `pytest tests/ -q`
  Expected: all passed

- [ ] Step 6: Commit
  ```bash
  git add tests/path/test_file.py src/path/file.py
  git commit -m "feat(scope): description"
  ```
```

**要求：**
- 完整测试代码和实现代码内联
- 每步 2-5 分钟
- 精确验证命令 + 预期输出
- 零上下文 agent 也能执行
- Constitution 条款逐条标注

---

## File Structure（Standard 和 Heavy 必须）

在 Tasks 之前锁定所有将创建或修改的文件：

```markdown
## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `src/module/core.py` | Create | 核心逻辑 |
| `src/module/types.py` | Create | 类型定义 |
| `tests/test_core.py` | Create | 核心逻辑测试 |
| `ARCHITECTURE.md` | Modify | 更新模块描述 |
```

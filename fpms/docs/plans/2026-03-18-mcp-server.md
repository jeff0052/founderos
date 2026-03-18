# FPMS MCP Server Implementation Plan

**Goal:** 把 FPMS 的接入方式从 shell exec 升级为 MCP Tool Server，保留 CLI 兼容  
**Architecture:** 新增 mcp_server.py 作为 transport 层，复用现有 ToolHandler + CommandExecutor，不改业务逻辑  
**Tech Stack:** Python 3.12, mcp SDK (FastMCP), 现有 FPMS spine 代码  
**FPMS Task:** task-a489  
**Module Spec:** 见下方  
**Risk Level:** L2（跨文件但边界清晰，不涉支付核心）  
**Plan Level:** Standard  
**Complexity Budget:** 新增 1 模块 / 最大 200 LOC / 依赖深度不变  
**Test Baseline:** `cd /Users/jeff/.openclaw/workspace/fpms && source .venv/bin/activate && python -m pytest tests/ -q` → 499 passed

---

## Module Spec: mcp_server.py

**职责：**
- 将 FPMS 14 个 tool 暴露为 MCP tools（stdio transport）
- 接收 JSON-RPC 请求，转发给 ToolHandler，返回结构化结果
- 长驻进程，一次初始化 DB，后续调用复用连接

**行为规则：**
- 每个 MCP tool 的参数 schema 必须与现有 Pydantic 模型一致
- 工具名保持与 spine.py CLI 一致（snake_case）
- 返回值保持与 ToolResult 一致的 JSON 结构
- 启动时初始化 DB + Store + CommandExecutor（复用现有 _get_executor 逻辑）
- command_id 自动生成（与 spine.py CLI 行为一致）

**约束：**
- 不修改任何现有文件（spine.py, spine/*.py, tests/*.py）
- 不引入新的业务逻辑
- 不改变 ToolHandler 的接口

### ⛔ 显式排除

- 不实现 HTTP/SSE transport（只做 stdio）
- 不实现 authentication
- 不实现 MCP resources 或 prompts（只做 tools）
- 不修改现有 CLI 入口
- 不修改现有测试

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `mcp_server.py` | Create | MCP Server 主入口，暴露 14 个 tools |
| `tests/test_mcp_server.py` | Create | MCP Server 单元测试 |

---

## Tasks

### Task 1: MCP Server Core

**Files:**
- Create: `mcp_server.py`
- Test: `tests/test_mcp_server.py`

**Exclusions:** 不做 HTTP transport, 不做 auth, 不做 resources/prompts, 不改现有文件
**Constitution:** §6(CLAUDE.md 同步) §9(TDD) §22(能删就不加)

- [ ] Step 1: Write failing test — server can be imported and tools are registered

  ```python
  def test_mcp_server_has_all_tools():
      """Verify all 14 FPMS tools are registered as MCP tools."""
      from mcp_server import mcp
      # FastMCP exposes tool names
      tool_names = {t.name for t in mcp._tool_manager.list_tools()}
      expected = {
          "create_node", "update_status", "update_field",
          "attach_node", "detach_node",
          "add_dependency", "remove_dependency",
          "append_log", "unarchive", "set_persistent",
          "shift_focus", "expand_context",
          "get_node", "search_nodes",
      }
      assert expected == tool_names
  ```

- [ ] Step 2: Run test, verify failure
  Run: `source .venv/bin/activate && python -m pytest tests/test_mcp_server.py::test_mcp_server_has_all_tools -v`
  Expected: FAIL — ModuleNotFoundError: No module named 'mcp_server'

- [ ] Step 3: Implement mcp_server.py — register all 14 tools with proper schemas

- [ ] Step 4: Run test → PASS

- [ ] Step 5: Write test — create_node tool works end-to-end

  ```python
  def test_create_node_via_mcp_tool(tmp_path):
      """Test that create_node MCP tool creates a node correctly."""
      import mcp_server
      # Override DB path for test isolation
      # Call the tool handler function directly
      result = ...  # invoke create_node with {"title": "test", "node_type": "task", "is_root": True}
      assert result["success"] is True
      assert result["data"]["title"] == "test"
  ```

- [ ] Step 6: Run test → PASS

- [ ] Step 7: Full suite → 499 + new tests all pass

- [ ] Step 8: Update CLAUDE.md with mcp_server.py entry

- [ ] Step 9: Commit: `feat(fpms): add MCP server transport layer`

---

## Acceptance Criteria

1. `mcp_server.py` 可以通过 `python mcp_server.py` 启动为 stdio MCP server
2. 14 个 FPMS tools 全部注册为 MCP tools
3. 每个 tool 的参数 schema 与现有 Pydantic 模型一致
4. 现有 499 tests 不受影响（零回归）
5. 新增测试覆盖 tool 注册 + 至少一个 tool 的端到端调用
6. CLAUDE.md 已更新

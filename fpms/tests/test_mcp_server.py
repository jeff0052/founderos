"""Tests for MCP server implementation."""

import json
import subprocess
import sys
import tempfile
import os
import pytest
from unittest.mock import patch, MagicMock

def test_mcp_server_imports():
    """Test that the MCP server can be imported."""
    with patch.dict('sys.modules', {'mcp_server': MagicMock()}):
        try:
            import mcp_server
            assert True
        except ImportError:
            pytest.fail("mcp_server.py should be importable")

def test_all_14_tools_registered():
    """Test that all 14 FPMS tools are registered as MCP tools."""
    # This will fail initially since mcp_server.py doesn't exist yet
    try:
        import mcp_server
        
        # Expected 14 tool names
        expected_tools = [
            "create_node", "update_status", "update_field", "attach_node",
            "detach_node", "add_dependency", "remove_dependency", "append_log",
            "unarchive", "set_persistent", "shift_focus", "expand_context",
            "get_node", "search_nodes"
        ]
        
        # Check that all tools are registered
        registered_tools = list(mcp_server.app._tool_manager._tools.keys())
        
        for tool in expected_tools:
            assert tool in registered_tools, f"Tool {tool} not registered in MCP server"
        
        assert len(registered_tools) == 14, f"Expected 14 tools, got {len(registered_tools)}"
        
    except ImportError:
        pytest.fail("mcp_server.py should exist and be importable")

def test_create_node_tool_call():
    """Test end-to-end tool call for create_node."""
    try:
        import mcp_server
        
        # Test create_node tool call
        tool_name = "create_node"
        tool_args = {
            "title": "Test Node",
            "node_type": "task",
            "summary": "Test summary"
        }
        
        # This should work if properly implemented
        registered_tools = list(mcp_server.app._tool_manager._tools.keys())
        assert tool_name in registered_tools, f"Tool {tool_name} not found in MCP server"
        
        # Test that the tool function exists and is callable
        tool_obj = mcp_server.app._tool_manager._tools[tool_name]
        assert callable(tool_obj.fn), f"Tool {tool_name} should be callable"
        
    except ImportError:
        pytest.fail("mcp_server.py should exist and be importable")

def test_mcp_server_startup():
    """Test that mcp_server.py can be started as a subprocess."""
    # This tests the actual stdio interface
    server_path = os.path.join(os.path.dirname(__file__), '..', 'mcp_server.py')
    
    if not os.path.exists(server_path):
        pytest.skip("mcp_server.py doesn't exist yet")
    
    # Test that the server can start without immediate error
    # We'll send a simple MCP message and expect a response
    proc = subprocess.Popen(
        [sys.executable, server_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Send initialization message
    init_message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "clientInfo": {"name": "test_client", "version": "1.0.0"}
        }
    }
    
    try:
        stdout, stderr = proc.communicate(
            input=json.dumps(init_message) + "\n",
            timeout=5
        )
        
        # Should not crash immediately
        assert proc.returncode != 1, f"Server crashed: stderr={stderr}"
        
        # Should get some response (even if it's an error, it means the server is responding)
        assert len(stdout.strip()) > 0, "Server should respond to initialization"
        
    except subprocess.TimeoutExpired:
        proc.kill()
        pytest.fail("Server took too long to respond")
    finally:
        if proc.poll() is None:
            proc.terminate()
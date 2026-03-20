#!/usr/bin/env python3
"""测试AI记忆工具的MCP集成

验证AI记忆工具是否正确集成到FPMS系统中
"""

import os
import tempfile
from spine.ai_memory_tools import AIMemoryTools


def test_ai_memory_tools_integration():
    """测试AI记忆工具集成"""
    print("🚀 测试AI记忆工具MCP集成...")
    
    # 创建临时数据库
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    
    try:
        # 初始化AI记忆工具
        ai_tools = AIMemoryTools(db_path)
        print("✅ AI记忆工具初始化成功")
        
        # 测试所有MCP工具函数
        test_cases = []
        
        # 1. 存储记忆
        print("\n1️⃣ 测试存储记忆...")
        result = ai_tools.store_memory(
            layer="constitution",
            topic="*",
            content="我是测试AI助手，这是测试记忆",
            relevance_score=1.0,
            metadata={"test": True}
        )
        print(f"存储结果: {result}")
        test_cases.append(("store_memory", result["success"]))
        
        # 2. 搜索记忆
        print("\n2️⃣ 测试搜索记忆...")
        result = ai_tools.memory_search(
            query="*",
            layers=["constitution"],
            limit=5
        )
        print(f"搜索结果: 找到 {result['found_count']} 条记忆")
        test_cases.append(("memory_search", result["success"] and result["found_count"] > 0))
        
        # 3. 加载Context
        print("\n3️⃣ 测试加载Context...")
        result = ai_tools.load_context(
            session_id="test_session",
            topic="*",
            include_layers=["constitution"]
        )
        print(f"Context加载结果: {result['success']}")
        if result["success"]:
            constitution_count = len(result["context"].get("constitution", []))
            print(f"加载了 {constitution_count} 条Constitution记忆")
        test_cases.append(("load_context", result["success"]))
        
        # 4. 存储更多记忆用于扩展测试
        ai_tools.store_memory(
            layer="judgment",
            topic="test_topic",
            content="这是测试判断记忆",
            relevance_score=0.8
        )
        
        # 5. 测试动态Context扩展
        print("\n4️⃣ 测试动态Context扩展...")
        result = ai_tools.expand_context(
            session_id="test_session",
            current_topic="*",
            search_query="test_topic",
            additional_layers=["judgment"]
        )
        print(f"动态扩展结果: 找到 {result['found_count']} 条额外记忆")
        test_cases.append(("expand_context", result["success"]))
        
        # 6. 测试对话记忆更新
        print("\n5️⃣ 测试对话记忆更新...")
        result = ai_tools.update_conversation_memory(
            session_id="test_session",
            topic="test_conversation",
            conversation_summary="这是测试对话摘要",
            new_insights=["测试洞察1", "测试洞察2"],
            decisions_made=["测试决策1"]
        )
        print(f"对话更新结果: {result['success']}")
        test_cases.append(("update_conversation", result["success"]))
        
        # 统计结果
        print("\n" + "="*50)
        print("📊 测试结果统计:")
        passed = 0
        total = len(test_cases)
        
        for test_name, success in test_cases:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"  {status} {test_name}")
            if success:
                passed += 1
        
        print(f"\n🎯 总体结果: {passed}/{total} 通过")
        
        if passed == total:
            print("🎉 所有AI记忆工具集成测试通过！")
        else:
            print("⚠️ 部分测试失败，需要检查集成问题")
        
        return passed == total
        
    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理
        if os.path.exists(db_path):
            os.unlink(db_path)
            print(f"\n🗑️ 清理测试数据库")


def test_mock_mcp_calls():
    """模拟MCP工具调用测试"""
    print("\n" + "="*50)
    print("🎭 模拟MCP工具调用测试")
    print("="*50)
    
    # 创建临时数据库
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    
    try:
        # 模拟MCP服务器环境
        ai_memory_tools = AIMemoryTools(db_path)
        
        # 模拟OpenClaw调用序列
        print("\n📞 模拟OpenClaw调用序列...")
        
        # 1. Session开始 - 加载Context
        print("\n1️⃣ Session开始，调用 ai_load_context...")
        context_result = ai_memory_tools.load_context(
            session_id="openclaw_session_001",
            topic="founderos_development",
            include_layers=["constitution", "office_memory"]
        )
        print(f"Context装载: {'成功' if context_result['success'] else '失败'}")
        
        # 2. 存储新记忆
        print("\n2️⃣ 存储工作记忆，调用 ai_store_memory...")
        store_result = ai_memory_tools.store_memory(
            layer="office_memory",
            topic="founderos_development",
            content="当前正在实施AI助手记忆系统，Phase 1已完成基础架构",
            relevance_score=0.9,
            metadata={"source": "openclaw_integration"}
        )
        print(f"记忆存储: {'成功' if store_result['success'] else '失败'}")
        
        # 3. 对话中检索
        print("\n3️⃣ 对话中检索，调用 ai_memory_search...")  
        search_result = ai_memory_tools.memory_search(
            query="founderos_development",
            layers=["office_memory", "judgment"],
            limit=5
        )
        print(f"记忆搜索: 找到 {search_result['found_count']} 条记忆")
        
        # 4. 对话结束 - 更新记忆
        print("\n4️⃣ 对话结束，调用 ai_update_conversation...")
        update_result = ai_memory_tools.update_conversation_memory(
            session_id="openclaw_session_001",
            topic="ai_memory_implementation",
            conversation_summary="成功完成AI记忆系统集成测试",
            new_insights=["MCP工具集成工作正常", "AI记忆系统可以与OpenClaw无缝集成"],
            decisions_made=["继续推进Phase 2: 记忆系统优化"]
        )
        print(f"对话记忆更新: {'成功' if update_result['success'] else '失败'}")
        
        print("\n🎉 OpenClaw集成模拟测试完成！")
        return True
        
    except Exception as e:
        print(f"❌ 模拟测试失败: {e}")
        return False
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def main():
    """主测试函数"""
    print("🔧 AI记忆工具MCP集成验证")
    
    # 测试工具集成
    basic_test_passed = test_ai_memory_tools_integration()
    
    # 测试模拟调用
    mock_test_passed = test_mock_mcp_calls()
    
    print("\n" + "="*60)
    print("📋 最终测试报告:")
    print(f"✅ 基础集成测试: {'通过' if basic_test_passed else '失败'}")
    print(f"✅ 模拟调用测试: {'通过' if mock_test_passed else '失败'}")
    
    if basic_test_passed and mock_test_passed:
        print("\n🎊 恭喜！AI记忆系统已成功集成到FPMS！")
        print("📡 MCP工具已就绪，可以为OpenClaw提供AI记忆功能")
        print("🚀 Phase 1: Context连续性验证 - 完成！")
    else:
        print("\n⚠️ 部分测试失败，需要进一步调试")
    
    print("="*60)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""测试AI助手记忆系统

验证六层记忆架构和Context装载功能
"""

import os
import tempfile
from spine.ai_memory import (
    AIMemory, 
    MemoryLayer, 
    AIMemoryStore, 
    ContextEngine, 
    MemoryUpdater,
    create_ai_memory_system
)


def setup_test_memories(memory_store: AIMemoryStore) -> None:
    """设置测试记忆数据"""
    
    # L1: Constitution - 角色记忆
    constitution_memories = [
        AIMemory(
            id="const_001",
            layer=MemoryLayer.CONSTITUTION,
            topic="*",
            content="我是Jeff的技术助手Claude，负责FounderOS架构设计和实现。我的行为原则：诚实、务实、第一性原理思考。",
            relevance_score=1.0
        ),
        AIMemory(
            id="const_002", 
            layer=MemoryLayer.CONSTITUTION,
            topic="*",
            content="Jeff是FounderOS的创始人，我们的目标是解决AI助手的认知连贯性问题，让AI成为真正的长期工作伙伴。",
            relevance_score=1.0
        )
    ]
    
    # L3: Judgment - 分析记忆
    judgment_memories = [
        AIMemory(
            id="judgment_001",
            layer=MemoryLayer.JUDGMENT,
            topic="founderos_architecture",
            content="六层记忆架构不是过度设计，每层对应AI助手必需的记忆类型。Constitution对应角色记忆，Fact对应项目状态，Judgment对应分析记忆等。",
            relevance_score=0.9
        ),
        AIMemory(
            id="judgment_002",
            layer=MemoryLayer.JUDGMENT, 
            topic="founderos_architecture",
            content="DCP(确定性Context推送)比纯RAG更适合AI助手记忆，因为可以确保重要信息被包含，避免检索不稳定问题。",
            relevance_score=0.8
        ),
        AIMemory(
            id="judgment_003",
            layer=MemoryLayer.JUDGMENT,
            topic="ai_memory_problem", 
            content="AI失忆的本质是Context断连问题，不是存储问题。每次新session时Context=空白导致认知不连贯。",
            relevance_score=0.9
        )
    ]
    
    # L4: Office Memory - 工作记忆
    office_memories = [
        AIMemory(
            id="office_001",
            layer=MemoryLayer.OFFICE_MEMORY,
            topic="founderos_development",
            content="作为技术助手，我负责：架构设计、代码实现、技术选型、质量保证。不负责：产品决策、对外沟通、业务运营。",
            relevance_score=1.0
        ),
        AIMemory(
            id="office_002",
            layer=MemoryLayer.OFFICE_MEMORY,
            topic="fpms_project",
            content="FPMS v1核心引擎已完成（494个测试全绿），Dashboard系统已上线，GitHub Pages已部署。下一步是实现AI助手记忆系统。",
            relevance_score=0.8
        )
    ]
    
    # L5: Narrative - 表述记忆  
    narrative_memories = [
        AIMemory(
            id="narrative_001",
            layer=MemoryLayer.NARRATIVE,
            topic="founderos_description",
            content="对外描述：FounderOS是一人公司操作系统，通过AI Agent替代COO/CTO角色，让Founder通过AI Office体系管理复杂公司。",
            relevance_score=1.0
        )
    ]
    
    # 存储所有测试记忆
    all_memories = constitution_memories + judgment_memories + office_memories + narrative_memories
    
    for memory in all_memories:
        memory_store.store_memory(memory)
        print(f"✅ 存储记忆: {memory.layer.value} - {memory.topic}")


def test_context_assembly(context_engine: ContextEngine) -> None:
    """测试Context组装功能"""
    print("\n🧠 测试Context组装...")
    
    # 测试场景：讨论FounderOS架构
    bundle = context_engine.assemble_context(
        session_id="test_session_001",
        topic="founderos_architecture"
    )
    
    print(f"\n📋 Context Bundle组装完成:")
    print(f"Session ID: {bundle.session_id}")
    print(f"Topic: {bundle.topic}")
    print(f"Assembled at: {bundle.assembled_at}")
    
    print(f"\n📝 Constitution记忆 ({len(bundle.constitution)}条):")
    for memory in bundle.constitution:
        print(f"  - {memory.content[:100]}...")
    
    print(f"\n🧐 Judgment记忆 ({len(bundle.judgments)}条):")
    for memory in bundle.judgments:
        print(f"  - {memory.content[:100]}...")
        
    print(f"\n💼 Office Memory ({len(bundle.office_memory)}条):")
    for memory in bundle.office_memory:
        print(f"  - {memory.content[:100]}...")


def test_dynamic_expansion(context_engine: ContextEngine) -> None:
    """测试动态Context扩展"""
    print("\n🔍 测试动态Context扩展...")
    
    # 模拟对话中需要更多信息的情况
    base_bundle = context_engine.assemble_context(
        session_id="test_session_002", 
        topic="ai_memory_problem"
    )
    
    # 动态检索"AI失忆"相关记忆
    additional_memories = context_engine.expand_context_dynamically(
        current_bundle=base_bundle,
        search_query="ai_memory_problem"
    )
    
    print(f"\n📚 动态检索到 {len(additional_memories)} 条相关记忆:")
    for memory in additional_memories:
        print(f"  - [{memory.layer.value}] {memory.content[:100]}...")


def test_memory_update(memory_updater: MemoryUpdater) -> None:
    """测试记忆更新功能"""
    print("\n📝 测试记忆更新...")
    
    # 模拟对话结束后的记忆更新
    memory_updater.update_from_conversation(
        session_id="test_session_003",
        topic="founderos_implementation",
        conversation_summary="讨论了AI助手记忆系统的实施方案，确定从扩展FPMS开始，实现六层记忆架构。",
        new_insights=[
            "混合DCP+动态检索策略比纯DCP更实用，可以处理预测失败的情况",
            "Context连续性是让AI从工具变成工作伙伴的关键技术"
        ],
        decisions_made=[
            "决定在FPMS基础上扩展AI助手记忆功能",
            "优先实现基础的memory_search和context装载功能"
        ]
    )
    
    print("✅ 记忆更新完成")


def main():
    """主测试函数"""
    print("🚀 开始测试AI助手记忆系统...")
    
    # 创建临时数据库
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    
    try:
        # 创建记忆系统
        memory_store, context_engine, memory_updater = create_ai_memory_system(db_path)
        print(f"✅ 记忆系统初始化完成: {db_path}")
        
        # 设置测试数据
        setup_test_memories(memory_store)
        
        # 测试Context组装
        test_context_assembly(context_engine)
        
        # 测试动态扩展
        test_dynamic_expansion(context_engine)
        
        # 测试记忆更新
        test_memory_update(memory_updater)
        
        print("\n🎉 所有测试完成！")
        print(f"💡 数据库位置: {db_path}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理临时文件
        if os.path.exists(db_path):
            os.unlink(db_path)
            print(f"🗑️ 清理临时数据库: {db_path}")


if __name__ == "__main__":
    main()
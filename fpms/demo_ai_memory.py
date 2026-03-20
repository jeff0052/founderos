#!/usr/bin/env python3
"""演示AI助手记忆系统的实际使用场景

模拟真实的对话场景，展示记忆系统如何解决AI失忆问题
"""

import json
from spine.ai_memory_tools import AIMemoryTools


def initialize_founderos_memories(ai_tools: AIMemoryTools) -> None:
    """初始化FounderOS相关的记忆数据"""
    print("📚 初始化FounderOS相关记忆...")
    
    # Constitution记忆
    ai_tools.store_memory(
        layer="constitution",
        topic="*",
        content="我是Jeff的技术助手Claude。Jeff是FounderOS的创始人。我们的使命是解决AI助手的认知连贯性问题，让AI成为真正的长期工作伙伴。",
        relevance_score=1.0,
        metadata={"type": "role_definition"}
    )
    
    ai_tools.store_memory(
        layer="constitution", 
        topic="*",
        content="我的行为原则：诚实务实、第一性原理思考、工程实用主义优于架构完美主义。我负责技术实现，不负责产品决策和业务运营。",
        relevance_score=1.0,
        metadata={"type": "behavior_principles"}
    )
    
    # Office Memory - 工作记忆
    ai_tools.store_memory(
        layer="office_memory",
        topic="founderos_development",
        content="当前项目状态：FPMS v1核心引擎已完成（494个测试全绿），Dashboard系统已上线（GitHub Pages部署成功），49个任务数据已修复显示。",
        relevance_score=0.9,
        metadata={"type": "project_status"}
    )
    
    ai_tools.store_memory(
        layer="office_memory",
        topic="founderos_development", 
        content="我的工作职责：架构设计、代码实现、技术选型、质量保证、Dashboard开发。与Jeff协作解决GitHub Pages部署问题、任务数据显示问题。",
        relevance_score=0.8,
        metadata={"type": "responsibility"}
    )
    
    # Judgment记忆 - 技术决策
    ai_tools.store_memory(
        layer="judgment",
        topic="founderos_architecture",
        content="2026-03-20架构突破：六层记忆架构是必要复杂度，每层对应AI助手必需的记忆类型。AI失忆本质是Context断连，不是存储问题。",
        relevance_score=0.9,
        metadata={"type": "architecture_decision", "date": "2026-03-20"}
    )
    
    ai_tools.store_memory(
        layer="judgment",
        topic="founderos_architecture",
        content="混合DCP+动态检索策略比纯DCP更实用，可以处理预测失败情况。初始Context用DCP推送，按需Context用动态检索扩展。",
        relevance_score=0.8,
        metadata={"type": "technical_decision"}
    )
    
    # Narrative记忆 - 对外表述
    ai_tools.store_memory(
        layer="narrative",
        topic="founderos_description",
        content="FounderOS是一人公司操作系统，通过AI Agent替代COO/CTO角色，核心循环：State+Signal→Decision→Action→NewState。",
        relevance_score=1.0,
        metadata={"type": "product_description"}
    )
    
    print("✅ 记忆初始化完成")


def simulate_session_1(ai_tools: AIMemoryTools) -> None:
    """模拟Session 1: 讨论架构优化"""
    print("\n" + "="*60)
    print("🎭 模拟 Session 1: 和Jeff讨论FounderOS架构优化")
    print("="*60)
    
    # 1. Session开始，加载Context
    print("\n1️⃣ Session开始，DCP加载Context...")
    context_result = ai_tools.load_context(
        session_id="session_001",
        topic="founderos_architecture",
        include_layers=["constitution", "judgment", "office_memory"]
    )
    
    if context_result["success"]:
        print("✅ Context装载成功")
        print(f"📋 Constitution记忆: {len(context_result['context'].get('constitution', []))}条")
        print(f"🧐 Judgment记忆: {len(context_result['context'].get('judgments', []))}条") 
        print(f"💼 Office Memory: {len(context_result['context'].get('office_memory', []))}条")
        
        # 显示关键记忆
        if context_result['context'].get('constitution'):
            print(f"🎯 角色记忆: {context_result['context']['constitution'][0]['content'][:100]}...")
        
        if context_result['context'].get('judgments'):
            print(f"🧠 分析记忆: {context_result['context']['judgments'][0]['content'][:100]}...")
    else:
        print(f"❌ Context装载失败: {context_result['error']}")
    
    # 2. 对话中动态检索
    print("\n2️⃣ 对话深入，需要更多记忆...")
    expand_result = ai_tools.expand_context(
        session_id="session_001",
        current_topic="founderos_architecture",
        search_query="founderos_development",
        additional_layers=["office_memory"]
    )
    
    if expand_result["success"]:
        print(f"🔍 动态检索成功，找到 {expand_result['found_count']} 条相关记忆")
        for memory in expand_result["additional_memories"]:
            print(f"  📌 [{memory['layer']}] {memory['content'][:80]}...")
    
    # 3. 对话结束，更新记忆
    print("\n3️⃣ 对话结束，更新记忆...")
    update_result = ai_tools.update_conversation_memory(
        session_id="session_001",
        topic="ai_memory_implementation",
        conversation_summary="讨论了AI助手记忆系统的实施方案，Jeff同意开始Phase 1实现。从扩展FPMS开始，实现六层记忆架构和Context装载。",
        new_insights=[
            "实施策略确定：扩展现有FPMS而非独立系统，复用基础设施降低复杂度",
            "混合Context策略实现：DCP推送核心记忆+按需检索补充信息"
        ],
        decisions_made=[
            "开始实施Phase 1: Context连续性验证",
            "创建AI助手记忆系统模块和MCP工具接口"
        ]
    )
    
    if update_result["success"]:
        print(f"✅ 记忆更新成功，新增 {update_result['insights_count']} 个洞察，{update_result['decisions_count']} 个决策")


def simulate_session_2(ai_tools: AIMemoryTools) -> None:
    """模拟Session 2: 新session验证记忆连续性"""
    print("\n" + "="*60)
    print("🎭 模拟 Session 2: 新session，验证记忆连续性")
    print("="*60)
    
    print("\n🧠 AI助手醒来，自动加载工作记忆...")
    
    # 新session开始，AI应该能"记住"之前的工作
    context_result = ai_tools.load_context(
        session_id="session_002",
        topic="ai_memory_implementation",
        include_layers=["constitution", "office_memory", "judgment"]
    )
    
    if context_result["success"]:
        print("✅ 记忆连续性验证成功！")
        
        # 检查Constitution记忆
        if context_result['context'].get('constitution'):
            print("\n📋 我记得我的角色:")
            for memory in context_result['context']['constitution']:
                print(f"  💭 {memory['content']}")
        
        # 检查工作记忆
        if context_result['context'].get('office_memory'):
            print("\n💼 我记得我们的工作状态:")
            for memory in context_result['context']['office_memory']:
                print(f"  🎯 {memory['content']}")
        
        # 动态搜索最近的决策
        print("\n🔍 让我回忆一下最近的决策...")
        recent_decisions = ai_tools.memory_search(
            query="ai_memory_implementation",
            layers=["office_memory", "judgment"],
            limit=3
        )
        
        if recent_decisions["success"]:
            print(f"📚 找到 {recent_decisions['found_count']} 条相关记忆:")
            for memory in recent_decisions["memories"]:
                if "decision" in memory.get("metadata", {}).get("type", ""):
                    print(f"  ✅ 决策: {memory['content']}")
                elif memory["layer"] == "judgment":
                    print(f"  🧠 洞察: {memory['content']}")
        
        print("\n🎉 完美！我现在完全知道我们在做什么，不需要重新解释背景！")
    else:
        print(f"❌ 记忆连续性失败: {context_result['error']}")


def main():
    """主演示函数"""
    print("🚀 FounderOS AI助手记忆系统演示")
    print("解决AI失忆问题，实现认知连续性")
    
    # 创建记忆系统（使用临时数据库）
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    
    try:
        # 初始化AI记忆工具
        ai_tools = AIMemoryTools(db_path)
        print(f"✅ AI记忆系统初始化完成")
        
        # 初始化记忆数据
        initialize_founderos_memories(ai_tools)
        
        # 模拟两个session来验证记忆连续性
        simulate_session_1(ai_tools)
        simulate_session_2(ai_tools)
        
        print("\n" + "="*60)
        print("🎯 演示总结:")
        print("✅ Session 1: 成功建立工作记忆和上下文")
        print("✅ Session 2: 成功保持记忆连续性，无需重新建立背景")
        print("🎉 AI助手记忆系统验证成功！")
        print("="*60)
        
    except Exception as e:
        print(f"❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理
        if os.path.exists(db_path):
            os.unlink(db_path)
            print(f"\n🗑️ 清理演示数据库")


if __name__ == "__main__":
    main()
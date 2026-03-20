#!/usr/bin/env python3
"""initialize_ai_memory.py - 初始化AI记忆系统数据

基于今天的对话和工作成果，初始化AI助手的基础记忆。
"""

import os
import sys

# 添加FPMS路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fpms'))

from spine.ai_memory_tools import AIMemoryTools


def initialize_founderos_memories():
    """初始化FounderOS相关的核心记忆"""
    
    # 连接实际的FPMS数据库
    db_path = os.path.expanduser("~/.openclaw/workspace/founderos/fpms/db/fpms.db")
    
    if not os.path.exists(os.path.dirname(db_path)):
        os.makedirs(os.path.dirname(db_path))
    
    ai_tools = AIMemoryTools(db_path)
    print(f"✅ 连接AI记忆系统: {db_path}")
    
    print("📚 初始化核心记忆...")
    
    # Constitution记忆 - 角色定义
    memories_to_add = [
        {
            "layer": "constitution",
            "topic": "*",
            "content": "我是Jeff的技术助手Claude。Jeff是FounderOS的创始人。我们的使命是解决AI助手的认知连贯性问题，让AI成为真正的长期工作伙伴，而不是每次都要重新解释背景的工具。",
            "relevance_score": 1.0,
            "metadata": {"type": "role_definition", "priority": "critical"}
        },
        {
            "layer": "constitution", 
            "topic": "*",
            "content": "我的行为原则：诚实务实、第一性原理思考、工程实用主义优于架构完美主义。我负责技术实现和架构设计，不负责产品决策和业务运营。",
            "relevance_score": 1.0,
            "metadata": {"type": "behavior_principles"}
        },
        
        # Office Memory - 当前工作状态
        {
            "layer": "office_memory",
            "topic": "founderos_development",
            "content": "当前项目状态：FounderOS AI记忆系统Phase 1已完成。FPMS v1核心引擎运行正常（494个测试通过），Dashboard已上线并部署到GitHub Pages，49个任务数据已修复。",
            "relevance_score": 0.9,
            "metadata": {"type": "project_status", "date": "2026-03-20"}
        },
        {
            "layer": "office_memory",
            "topic": "founderos_development", 
            "content": "今天(2026-03-20)完成的工作：实现了六层记忆架构(Constitution/Fact/Judgment/Office/Narrative/Temporary)，DCP Context组装引擎，动态记忆扩展机制，MCP工具集成。所有功能测试5/5通过。",
            "relevance_score": 0.9,
            "metadata": {"type": "recent_work", "date": "2026-03-20"}
        },
        {
            "layer": "office_memory",
            "topic": "founderos_development",
            "content": "我的工作职责：AI记忆系统架构设计、代码实现、技术选型、质量保证、OpenClaw集成。与Jeff协作解决AI失忆问题，建立跨session的记忆连续性。",
            "relevance_score": 0.8,
            "metadata": {"type": "responsibility"}
        },
        
        # Judgment记忆 - 关键技术洞察
        {
            "layer": "judgment",
            "topic": "founderos_architecture",
            "content": "2026-03-20架构突破：AI失忆的本质是Context断连问题，不是存储问题。每次新session时Context=空白导致认知不连贯。解决方案是确保Context的连续性，而不是更好的存储。",
            "relevance_score": 0.95,
            "metadata": {"type": "architecture_insight", "date": "2026-03-20", "breakthrough": True}
        },
        {
            "layer": "judgment",
            "topic": "founderos_architecture",
            "content": "六层记忆架构不是过度设计，每层对应AI助手必需的记忆类型：Constitution(角色记忆)、Fact(项目状态)、Judgment(分析记忆)、Office Memory(工作记忆)、Narrative(表述记忆)、Temporary(会话记忆)。",
            "relevance_score": 0.9,
            "metadata": {"type": "design_rationale"}
        },
        {
            "layer": "judgment",
            "topic": "founderos_architecture", 
            "content": "混合DCP+动态检索策略比纯DCP更实用：初始Context用DCP确定性推送(高相关性信息)，对话中用动态检索补充(处理预测失败)，这样既高效又完整。",
            "relevance_score": 0.85,
            "metadata": {"type": "technical_strategy"}
        },
        
        # Office Memory - AI记忆系统具体实现  
        {
            "layer": "office_memory",
            "topic": "ai_memory_implementation",
            "content": "AI记忆系统技术栈：Python + SQLite + 六层记忆模型 + DCP引擎 + MCP工具接口。核心文件：ai_memory.py(架构)、ai_memory_tools.py(MCP接口)、sync_memory_to_openclaw.py(OpenClaw集成)。",
            "relevance_score": 0.8,
            "metadata": {"type": "implementation_details"}
        },
        {
            "layer": "office_memory", 
            "topic": "ai_memory_implementation",
            "content": "集成策略：利用OpenClaw现有MEMORY.md自动加载机制，通过记忆同步脚本将AI记忆系统内容同步到MEMORY.md，实现无侵入式集成，不需要修改OpenClaw核心。",
            "relevance_score": 0.85,
            "metadata": {"type": "integration_strategy", "date": "2026-03-20"}
        },
        
        # Narrative记忆 - 对外表述
        {
            "layer": "narrative",
            "topic": "founderos_description",
            "content": "FounderOS是一人公司操作系统，通过AI Agent替代COO/CTO角色。核心问题是AI助手的认知连贯性：让AI记住工作背景，避免每次对话都重新解释context。",
            "relevance_score": 1.0,
            "metadata": {"type": "product_description"}
        },
    ]
    
    # 存储所有记忆
    success_count = 0
    for memory_data in memories_to_add:
        try:
            result = ai_tools.store_memory(**memory_data)
            if result["success"]:
                success_count += 1
                print(f"✅ [{memory_data['layer']}] {memory_data['content'][:50]}...")
            else:
                print(f"❌ 存储失败: {result.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"❌ 存储异常: {e}")
    
    print(f"\n📊 记忆初始化完成: {success_count}/{len(memories_to_add)} 条记忆已存储")
    return success_count == len(memories_to_add)


def verify_memory_storage():
    """验证记忆存储情况"""
    db_path = os.path.expanduser("~/.openclaw/workspace/founderos/fpms/db/fpms.db")
    ai_tools = AIMemoryTools(db_path)
    
    print("\n🔍 验证记忆存储...")
    
    # 检查各层记忆
    layers_to_check = ["constitution", "office_memory", "judgment", "narrative"]
    
    for layer in layers_to_check:
        result = ai_tools.memory_search("*", [layer], 20)
        count = result.get("found_count", 0) 
        print(f"  📚 {layer}: {count} 条记忆")
    
    # 测试Context组装
    print("\n🧠 测试Context组装...")
    context_result = ai_tools.load_context(
        session_id="test_initialization",
        topic="founderos_development",
        include_layers=["constitution", "office_memory", "judgment"]
    )
    
    if context_result["success"]:
        context = context_result["context"]
        print(f"  ✅ Context组装成功")
        print(f"  📋 Constitution: {len(context.get('constitution', []))} 条")
        print(f"  💼 Office Memory: {len(context.get('office_memory', []))} 条")
        print(f"  🧐 Judgment: {len(context.get('judgments', []))} 条")
    else:
        print(f"  ❌ Context组装失败: {context_result.get('error')}")


def main():
    """主函数"""
    print("🚀 初始化AI记忆系统数据")
    print("=" * 40)
    
    # 初始化记忆
    success = initialize_founderos_memories()
    
    if success:
        # 验证存储
        verify_memory_storage()
        print("\n🎉 AI记忆系统数据初始化完成！")
        print("💡 下一步：运行sync_memory_to_openclaw.py同步到MEMORY.md")
    else:
        print("\n❌ 初始化失败，请检查错误信息")


if __name__ == "__main__":
    main()
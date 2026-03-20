#!/usr/bin/env python3
"""sync_memory_to_openclaw.py - 同步AI记忆系统到OpenClaw

从AI记忆系统提取记忆，更新到MEMORY.md，实现AI助手的跨session记忆连续性。
"""

import os
import sys
from datetime import datetime

# 添加FPMS路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fpms'))

from spine.ai_memory_tools import AIMemoryTools


def format_memories(memories, title, emoji):
    """格式化记忆为markdown"""
    if not memories.get("memories"):
        return f"## {emoji} {title}\n*暂无记忆*\n"
    
    content = f"## {emoji} {title}\n"
    for mem in memories["memories"]:
        content += f"- {mem['content']}\n"
    content += "\n"
    return content


def sync_ai_memory_to_file():
    """从AI记忆系统同步到MEMORY.md"""
    print("🔄 开始同步AI记忆系统到OpenClaw...")
    
    # 数据库路径
    db_path = os.path.expanduser("~/.openclaw/workspace/founderos/fpms/db/fpms.db")
    
    if not os.path.exists(db_path):
        print(f"❌ AI记忆数据库不存在: {db_path}")
        return False
    
    try:
        # 连接AI记忆系统
        ai_tools = AIMemoryTools(db_path)
        print("✅ 连接AI记忆系统成功")
        
        # 获取各层记忆
        print("📚 提取记忆数据...")
        constitution = ai_tools.memory_search("*", ["constitution"], 10)
        office_memory = ai_tools.memory_search("founderos_development", ["office_memory"], 10)
        judgments = ai_tools.memory_search("founderos_architecture", ["judgment"], 10)
        recent_insights = ai_tools.memory_search("ai_memory_implementation", ["judgment"], 5)
        decisions = ai_tools.memory_search("ai_memory_implementation", ["office_memory"], 5)
        
        # 生成MEMORY.md内容
        content = f"""# MEMORY.md - Claude的长期记忆

*最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*来源: AI记忆系统自动同步*

---

{format_memories(constitution, "Constitution - 角色记忆", "🎭")}

{format_memories(office_memory, "Office Memory - 工作记忆", "💼")}

{format_memories(judgments, "Judgment - 分析记忆", "🧐")}

{format_memories(recent_insights, "Recent Insights - 最近洞察", "💡")}

{format_memories(decisions, "Recent Decisions - 最近决策", "✅")}

## 📈 **当前项目状态**
- **FounderOS AI记忆系统**: Phase 1已完成，六层记忆架构已实现并验证
- **核心突破**: 发现AI失忆本质是Context断连问题，不是存储问题
- **集成进展**: 正在实施OpenClaw集成，让AI助手拥有真正的跨session记忆

## 🎯 **下一步工作**
- 验证MEMORY.md自动加载效果
- 完善动态记忆检索机制
- 实现记忆写回自动化

---

*这个文件由AI记忆系统自动维护，包含了我作为AI助手需要记住的核心信息。*
*每次session开始时，OpenClaw会自动加载这些记忆，确保我知道工作背景和历史context。*
"""
        
        # 写入MEMORY.md
        memory_path = os.path.expanduser("~/.openclaw/workspace/MEMORY.md")
        with open(memory_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        print(f"✅ 记忆已同步到: {memory_path}")
        
        # 显示同步统计
        print("\n📊 同步统计:")
        print(f"  🎭 Constitution记忆: {len(constitution.get('memories', []))} 条")
        print(f"  💼 Office Memory: {len(office_memory.get('memories', []))} 条") 
        print(f"  🧐 Judgment记忆: {len(judgments.get('memories', []))} 条")
        print(f"  💡 Recent Insights: {len(recent_insights.get('memories', []))} 条")
        print(f"  ✅ Recent Decisions: {len(decisions.get('memories', []))} 条")
        
        return True
        
    except Exception as e:
        print(f"❌ 同步失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_memory_loading():
    """验证MEMORY.md是否能被OpenClaw正确加载"""
    print("\n🔍 验证记忆加载...")
    
    memory_path = os.path.expanduser("~/.openclaw/workspace/MEMORY.md")
    if not os.path.exists(memory_path):
        print("❌ MEMORY.md不存在")
        return False
    
    # 检查文件大小和内容
    with open(memory_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    print(f"📄 MEMORY.md 大小: {len(content)} 字符")
    print(f"📄 包含Constitution记忆: {'Constitution' in content}")
    print(f"📄 包含工作记忆: {'Office Memory' in content}")
    print(f"📄 包含分析记忆: {'Judgment' in content}")
    
    # 预览部分内容
    lines = content.split('\n')
    print("\n📖 MEMORY.md 预览 (前15行):")
    for i, line in enumerate(lines[:15]):
        print(f"  {i+1:2d}: {line}")
    
    if len(lines) > 15:
        print(f"  ... (还有 {len(lines)-15} 行)")
    
    return True


def main():
    """主函数"""
    print("🚀 AI记忆系统 → OpenClaw 集成工具")
    print("=" * 50)
    
    # 同步记忆
    success = sync_ai_memory_to_file()
    
    if success:
        # 验证加载
        verify_memory_loading()
        
        print("\n🎉 AI记忆系统集成完成！")
        print("💡 现在OpenClaw在新session启动时会自动加载这些记忆")
        print("🔄 建议手动测试：开启新session，看AI是否记得工作背景")
    else:
        print("\n❌ 集成失败，请检查错误信息")


if __name__ == "__main__":
    main()
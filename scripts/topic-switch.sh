#!/bin/bash

# Topic Switch - 话题切换助手
# Usage: ./topic-switch.sh [new|status|help]

WORKSPACE_DIR="$HOME/.openclaw/workspace"
TOPICS_FILE="$WORKSPACE_DIR/memory/current-topics.md"

show_current_topics() {
    echo "📍 当前活跃话题:"
    
    if [[ -f "$TOPICS_FILE" ]]; then
        cat "$TOPICS_FILE"
    else
        echo "  (无活跃话题记录)"
    fi
    
    echo ""
    echo "📊 本 session 状态:"
    openclaw session status --compact 2>/dev/null || echo "  Context: 未知"
}

suggest_new_topic() {
    local current_context=$(openclaw session status --json 2>/dev/null | grep -o '"contextSize":[0-9]*' | cut -d: -f2 || echo "0")
    
    if [[ $current_context -gt 80000 ]]; then
        echo "⚠️  当前 Context: ${current_context}k"
        echo "💡 建议开新话题避免限流:"
        echo "   /new"
        echo ""
    fi
    
    echo "🚀 快速切换话题:"
    echo "   1. 记录当前话题状态"
    echo "   2. /new 开启新对话"
    echo "   3. 在新 session 处理独立问题"
    echo ""
    echo "📝 话题记录模板:"
    echo "# 话题: [简短描述]"
    echo "## 状态: [进行中/已完成/待续]" 
    echo "## 下一步: [具体行动]"
    echo "## Session: [session-key]"
}

add_topic() {
    local topic_name="$1"
    local session_key="$2"
    
    if [[ -z "$topic_name" ]]; then
        echo "用法: ./topic-switch.sh add '话题名称' [session-key]"
        return 1
    fi
    
    mkdir -p "$(dirname "$TOPICS_FILE")"
    
    if [[ ! -f "$TOPICS_FILE" ]]; then
        echo "# 当前活跃话题" > "$TOPICS_FILE"
        echo "" >> "$TOPICS_FILE"
    fi
    
    echo "## 📌 $topic_name" >> "$TOPICS_FILE"
    echo "- 状态: 进行中" >> "$TOPICS_FILE"
    echo "- 开始: $(date '+%Y-%m-%d %H:%M')" >> "$TOPICS_FILE"
    if [[ -n "$session_key" ]]; then
        echo "- Session: $session_key" >> "$TOPICS_FILE"
    fi
    echo "" >> "$TOPICS_FILE"
    
    echo "✅ 话题已记录: $topic_name"
}

show_help() {
    echo "Topic Switch - 话题切换助手"
    echo ""
    echo "用法:"
    echo "  ./topic-switch.sh status           显示当前话题"
    echo "  ./topic-switch.sh new              建议新话题切换"
    echo "  ./topic-switch.sh add '话题名'      记录新话题"
    echo "  ./topic-switch.sh help             显示帮助"
    echo ""
    echo "工作流程:"
    echo "  1. 当前话题告一段落时: ./topic-switch.sh add '当前话题总结'"
    echo "  2. 开始新问题前: ./topic-switch.sh new"
    echo "  3. 根据建议决定是否 /new 开新 session"
}

# 主逻辑
case "${1:-status}" in
    status)
        show_current_topics
        ;;
    new)
        suggest_new_topic
        ;;
    add)
        add_topic "$2" "$3"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "❌ 未知命令: $1"
        show_help
        exit 1
        ;;
esac
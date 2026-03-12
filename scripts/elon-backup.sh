#!/bin/bash

# Elon System Backup & Migration Script
# Usage: ./elon-backup.sh [backup|restore] [backup-file]

WORKSPACE_DIR="$HOME/.openclaw/workspace"
SHARED_MEMORY_DIR="$HOME/.openclaw/shared-memory"
BACKUP_PREFIX="elon-backup"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

backup_system() {
    local backup_file="${BACKUP_PREFIX}-${TIMESTAMP}.tar.gz"
    
    echo "🚀 开始备份 Elon 系统..."
    
    # 检查目录是否存在
    if [[ ! -d "$WORKSPACE_DIR" ]]; then
        echo "❌ 工作区目录不存在: $WORKSPACE_DIR"
        exit 1
    fi
    
    # 创建临时目录
    local temp_dir=$(mktemp -d)
    local backup_root="$temp_dir/elon"
    
    echo "📁 准备备份内容..."
    mkdir -p "$backup_root"
    
    # 备份 workspace (排除大文件和缓存)
    echo "  📋 备份工作区..."
    rsync -av --exclude='.git' --exclude='node_modules' --exclude='*.log' \
          --exclude='*.tmp' --exclude='.DS_Store' \
          "$WORKSPACE_DIR/" "$backup_root/workspace/"
    
    # 备份共享内存
    if [[ -d "$SHARED_MEMORY_DIR" ]]; then
        echo "  🧠 备份共享内存..."
        rsync -av "$SHARED_MEMORY_DIR/" "$backup_root/shared-memory/"
    fi
    
    # 备份 OpenClaw 配置
    if [[ -f "$HOME/.openclaw/config.json" ]]; then
        echo "  ⚙️ 备份配置文件..."
        cp "$HOME/.openclaw/config.json" "$backup_root/"
    fi
    
    # 生成系统信息
    echo "  📊 生成系统信息..."
    cat > "$backup_root/system-info.txt" << EOF
Elon System Backup
==================
Backup Time: $(date)
Host: $(hostname)
OS: $(uname -a)
OpenClaw Version: $(openclaw --version 2>/dev/null || echo "N/A")
Workspace Size: $(du -sh "$WORKSPACE_DIR" | cut -f1)

Included:
- Workspace directory
- Shared memory
- Configuration files
- System metadata

Excluded:
- Git history
- Node modules
- Log files
- Cache files
EOF

    # 打包压缩
    echo "  📦 压缩打包..."
    tar -czf "$backup_file" -C "$temp_dir" elon
    
    # 清理临时文件
    rm -rf "$temp_dir"
    
    # 显示结果
    local backup_size=$(du -sh "$backup_file" | cut -f1)
    echo "✅ 备份完成!"
    echo "📁 文件: $backup_file"
    echo "📏 大小: $backup_size"
    echo ""
    echo "🔄 恢复命令:"
    echo "  ./elon-backup.sh restore $backup_file"
}

restore_system() {
    local backup_file="$1"
    
    if [[ -z "$backup_file" ]]; then
        echo "❌ 请指定备份文件"
        echo "用法: ./elon-backup.sh restore <backup-file>"
        exit 1
    fi
    
    if [[ ! -f "$backup_file" ]]; then
        echo "❌ 备份文件不存在: $backup_file"
        exit 1
    fi
    
    echo "🔄 开始恢复 Elon 系统..."
    echo "📁 备份文件: $backup_file"
    
    # 确认操作
    read -p "⚠️  这将覆盖现有系统，确认继续? (y/N): " confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        echo "❌ 取消恢复"
        exit 0
    fi
    
    # 创建临时目录
    local temp_dir=$(mktemp -d)
    
    echo "📦 解压备份文件..."
    tar -xzf "$backup_file" -C "$temp_dir"
    
    local backup_root="$temp_dir/elon"
    
    if [[ ! -d "$backup_root" ]]; then
        echo "❌ 备份文件格式错误"
        rm -rf "$temp_dir"
        exit 1
    fi
    
    # 备份现有系统
    if [[ -d "$WORKSPACE_DIR" ]]; then
        echo "📋 备份现有工作区..."
        mv "$WORKSPACE_DIR" "${WORKSPACE_DIR}.backup.$(date +%s)"
    fi
    
    if [[ -d "$SHARED_MEMORY_DIR" ]]; then
        echo "🧠 备份现有共享内存..."
        mv "$SHARED_MEMORY_DIR" "${SHARED_MEMORY_DIR}.backup.$(date +%s)"
    fi
    
    # 恢复系统
    echo "📁 恢复工作区..."
    mkdir -p "$(dirname "$WORKSPACE_DIR")"
    cp -r "$backup_root/workspace" "$WORKSPACE_DIR"
    
    if [[ -d "$backup_root/shared-memory" ]]; then
        echo "🧠 恢复共享内存..."
        mkdir -p "$(dirname "$SHARED_MEMORY_DIR")"
        cp -r "$backup_root/shared-memory" "$SHARED_MEMORY_DIR"
    fi
    
    if [[ -f "$backup_root/config.json" ]]; then
        echo "⚙️ 恢复配置文件..."
        mkdir -p "$(dirname "$HOME/.openclaw/config.json")"
        cp "$backup_root/config.json" "$HOME/.openclaw/config.json"
    fi
    
    # 显示系统信息
    if [[ -f "$backup_root/system-info.txt" ]]; then
        echo ""
        echo "📊 备份系统信息:"
        cat "$backup_root/system-info.txt"
    fi
    
    # 清理临时文件
    rm -rf "$temp_dir"
    
    echo ""
    echo "✅ 恢复完成!"
    echo "🔧 下一步:"
    echo "  1. 检查 API keys 配置"
    echo "  2. 更新本地路径设置"
    echo "  3. 重启 OpenClaw: openclaw gateway restart"
}

list_backups() {
    echo "📁 可用的备份文件:"
    ls -la ${BACKUP_PREFIX}-*.tar.gz 2>/dev/null || echo "  (无备份文件)"
}

show_help() {
    echo "Elon System Backup & Migration Tool"
    echo ""
    echo "用法:"
    echo "  ./elon-backup.sh backup           创建备份"
    echo "  ./elon-backup.sh restore <file>   恢复备份"
    echo "  ./elon-backup.sh list             列出备份"
    echo "  ./elon-backup.sh help             显示帮助"
    echo ""
    echo "示例:"
    echo "  ./elon-backup.sh backup"
    echo "  ./elon-backup.sh restore elon-backup-20260312-203900.tar.gz"
}

# 主逻辑
case "${1:-help}" in
    backup)
        backup_system
        ;;
    restore)
        restore_system "$2"
        ;;
    list)
        list_backups
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
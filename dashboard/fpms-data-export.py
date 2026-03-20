#!/usr/bin/env python3
"""
FPMS Data Export - 生成 Dashboard 所需的实时数据
"""

import json
import sqlite3
from datetime import datetime
from dataclasses import asdict

def export_fpms_data(db_path="founderos/fpms/db/fpms.db"):
    """导出 FPMS 数据为 JSON 格式"""
    
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    
    data = {
        "exported_at": datetime.now().isoformat(),
        "goals": [],
        "projects": [],
        "tasks": [],
        "memories": [],
        "stats": {}
    }
    
    # Goals
    goals = db.execute('SELECT * FROM nodes WHERE node_type = "goal" ORDER BY status, title').fetchall()
    for g in goals:
        data["goals"].append({
            "id": g["id"],
            "title": g["title"], 
            "status": g["status"],
            "summary": g["summary"],
            "updated_at": g["updated_at"]
        })
    
    # Projects with task counts
    projects = db.execute('SELECT * FROM nodes WHERE node_type = "project" ORDER BY status, title').fetchall()
    for p in projects:
        task_counts = db.execute('''
            SELECT status, COUNT(*) as count 
            FROM nodes 
            WHERE parent_id = ? 
            GROUP BY status
        ''', (p['id'],)).fetchall()
        
        task_stats = {tc['status']: tc['count'] for tc in task_counts}
        
        data["projects"].append({
            "id": p["id"],
            "title": p["title"],
            "status": p["status"],
            "summary": p["summary"],
            "parent_id": p["parent_id"],
            "task_counts": task_stats,
            "total_tasks": sum(task_stats.values()),
            "updated_at": p["updated_at"]
        })
    
    # Task status distribution
    task_status = db.execute('''
        SELECT status, COUNT(*) as count 
        FROM nodes 
        WHERE node_type = "task" 
        GROUP BY status
    ''').fetchall()
    
    data["stats"]["task_distribution"] = {ts['status']: ts['count'] for ts in task_status}
    
    # Project status distribution
    project_status = db.execute('''
        SELECT status, COUNT(*) as count 
        FROM nodes 
        WHERE node_type = "project" 
        GROUP BY status
    ''').fetchall()
    
    data["stats"]["project_distribution"] = {ps['status']: ps['count'] for ps in project_status}
    
    # Recent activity
    recent = db.execute('''
        SELECT id, title, status, node_type, updated_at
        FROM nodes 
        ORDER BY updated_at DESC 
        LIMIT 10
    ''').fetchall()
    
    data["recent_activity"] = []
    for r in recent:
        data["recent_activity"].append({
            "id": r["id"],
            "title": r["title"],
            "status": r["status"],
            "node_type": r["node_type"],
            "updated_at": r["updated_at"]
        })
    
    # Memory stats (if available)
    try:
        memories = db.execute('''
            SELECT layer, priority, COUNT(*) as count 
            FROM memories 
            GROUP BY layer, priority 
            ORDER BY layer, priority
        ''').fetchall()
        
        data["stats"]["memory_distribution"] = {}
        for m in memories:
            layer = m["layer"]
            if layer not in data["stats"]["memory_distribution"]:
                data["stats"]["memory_distribution"][layer] = {}
            data["stats"]["memory_distribution"][layer][f"P{m['priority']}"] = m["count"]
            
    except sqlite3.OperationalError:
        data["stats"]["memory_distribution"] = {}
    
    # Overall stats
    total_nodes = db.execute('SELECT COUNT(*) as count FROM nodes').fetchone()
    total_tasks = sum(data["stats"]["task_distribution"].values()) if data["stats"]["task_distribution"] else 0
    completed_tasks = data["stats"]["task_distribution"].get("done", 0)
    
    data["stats"]["overview"] = {
        "total_nodes": total_nodes["count"],
        "total_goals": len(data["goals"]),
        "total_projects": len(data["projects"]),
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "completion_rate": round(completed_tasks / total_tasks * 100, 1) if total_tasks > 0 else 0
    }
    
    db.close()
    return data

if __name__ == "__main__":
    import sys
    
    # 导出数据
    data = export_fpms_data()
    
    # 输出到文件或标准输出
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Data exported to {sys.argv[1]}")
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))
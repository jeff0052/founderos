#!/usr/bin/env python3
"""
FPMS Dashboard API
提供JSON格式的数据给前端Dashboard使用
"""

import sys
import os
import json
from datetime import datetime

# 添加FPMS路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../fpms'))

try:
    from spine.store import FPMSStore
    from spine.models import NodeType, NodeStatus
    from spine.memory import MemoryStore
    
    def get_dashboard_data():
        """获取Dashboard所需的完整数据"""
        fpms = FPMSStore()
        memory = MemoryStore()
        
        # 获取所有节点
        all_nodes = fpms.list_all_nodes()
        goals = [n for n in all_nodes if n['node_type'] == NodeType.GOAL.value]
        projects = [n for n in all_nodes if n['node_type'] == NodeType.PROJECT.value]  
        tasks = [n for n in all_nodes if n['node_type'] == NodeType.TASK.value]
        
        # 为项目添加任务统计
        for project in projects:
            project_tasks = [t for t in tasks if t.get('parent_id') == project['id']]
            task_counts = {}
            for task in project_tasks:
                status = task.get('status', 'unknown')
                task_counts[status] = task_counts.get(status, 0) + 1
            project['task_counts'] = task_counts
            project['total_tasks'] = len(project_tasks)
            project['tasks'] = project_tasks  # 包含完整任务列表
        
        # 获取记忆数据  
        memories = memory.list_all_memories()
        
        # 统计数据
        task_distribution = {}
        for task in tasks:
            status = task.get('status', 'unknown')
            task_distribution[status] = task_distribution.get(status, 0) + 1
            
        project_distribution = {}
        for project in projects:
            status = project.get('status', 'unknown') 
            project_distribution[status] = project_distribution.get(status, 0) + 1
            
        # 记忆分布统计
        memory_distribution = {}
        for mem in memories:
            layer = mem.get('layer', 'unknown')
            priority = mem.get('priority', 'unknown')
            
            if layer not in memory_distribution:
                memory_distribution[layer] = {}
            memory_distribution[layer][priority] = memory_distribution[layer].get(priority, 0) + 1
        
        # 最近活动（按更新时间排序）
        recent_activity = []
        for node in all_nodes:
            if node.get('updated_at'):
                recent_activity.append({
                    'id': node['id'],
                    'title': node['title'], 
                    'status': node['status'],
                    'node_type': node['node_type'],
                    'updated_at': node['updated_at']
                })
        
        recent_activity.sort(key=lambda x: x['updated_at'], reverse=True)
        recent_activity = recent_activity[:10]  # 最近10条
        
        # 从所有项目中收集任务到顶层数组
        all_tasks = []
        for project in projects:
            if 'tasks' in project:
                all_tasks.extend(project['tasks'])
        
        # 组装完整数据
        data = {
            'exported_at': datetime.now().isoformat(),
            'goals': goals,
            'projects': projects,
            'tasks': all_tasks,  # 使用收集的所有任务
            'memories': memories,
            'stats': {
                'task_distribution': task_distribution,
                'project_distribution': project_distribution,
                'memory_distribution': memory_distribution,
                'overview': {
                    'total_nodes': len(all_nodes),
                    'total_goals': len(goals),
                    'total_projects': len(projects), 
                    'total_tasks': len(tasks),
                    'completed_tasks': task_distribution.get('done', 0),
                    'completion_rate': round(task_distribution.get('done', 0) / len(tasks) * 100, 1) if tasks else 0
                }
            },
            'recent_activity': recent_activity
        }
        
        return data
        
except ImportError as e:
    print(f"Warning: FPMS modules not available: {e}", file=sys.stderr)
    
    def get_dashboard_data():
        """返回示例数据"""
        return {
            "exported_at": datetime.now().isoformat(),
            "goals": [
                {
                    "id": "goal-ced834",
                    "title": "BinancePay", 
                    "status": "active",
                    "summary": "支付公司核心业务 — 与 Binance 合作的支付项目。三条线：国家码支付、PSP/TSP 接入 Binance Pay、On-chain/On-ramping。FounderOS 第一个实战管理场景。",
                    "updated_at": "2026-03-19T06:48:44.700245+00:00"
                },
                {
                    "id": "goal-6c8a", 
                    "title": "FounderOS",
                    "status": "active",
                    "summary": "一人公司的底层操作系统 — 让一个 Founder 通过 AI Office 体系管理整家公司。核心循环 State+Signal→Decision→Action→NewState。V3 阶段：FPMS（State）已建，CTO Agent（第一个 Office）待搭建。",
                    "updated_at": "2026-03-17T15:43:44.076018+00:00"
                }
            ],
            "projects": [
                {
                    "id": "project-4acae1",
                    "title": "BinancePay",
                    "status": "active", 
                    "summary": "与 Binance 的支付合作项目。三条线：1) 国家码支付合作（SG/PH/VN/JP/TH）2) PSP/TSP 接入 Binance Pay 3) On-chain/On-ramping 服务",
                    "parent_id": "goal-ced834",
                    "task_counts": {"inbox": 4},
                    "total_tasks": 4,
                    "tasks": [
                        {
                            "id": "task-8570d3",
                            "title": "回复 Binance：5 区域 provider/timeline/rate/FX markup",
                            "status": "inbox",
                            "parent_id": "project-4acae1",
                            "summary": "需要回复 Binance 关于5个区域的详细信息",
                            "updated_at": "2026-03-19T06:46:43.191583+00:00"
                        },
                        {
                            "id": "task-43a7ad", 
                            "title": "注册 Binance TSP 账户 + KYB",
                            "status": "inbox",
                            "parent_id": "project-4acae1",
                            "summary": "完成 Binance TSP 注册和 KYB 认证",
                            "updated_at": "2026-03-19T06:46:43.319899+00:00"
                        },
                        {
                            "id": "task-85b97c",
                            "title": "PSP 分润方案确定 + 邮件提交 Binance", 
                            "status": "inbox",
                            "parent_id": "project-4acae1",
                            "summary": "确定PSP分润方案并提交给 Binance",
                            "updated_at": "2026-03-19T06:46:43.447353+00:00"
                        },
                        {
                            "id": "task-bc1a73",
                            "title": "On-ramping 方案评估",
                            "status": "inbox", 
                            "parent_id": "project-4acae1",
                            "summary": "评估 On-ramping 技术和商业方案",
                            "updated_at": "2026-03-19T06:46:43.575079+00:00"
                        }
                    ],
                    "updated_at": "2026-03-19T06:48:06.661769+00:00"
                },
                {
                    "id": "project-a501",
                    "title": "CTO Agent",
                    "status": "active",
                    "summary": "能开发维护大型系统的 AI CTO — 从小开始，快速迭代，最终具备独立交付复杂产品的能力（如支付系统级别）",
                    "parent_id": "goal-6c8a",
                    "task_counts": {"active": 1, "done": 4, "inbox": 5},
                    "total_tasks": 10,
                    "tasks": [
                        {
                            "id": "task-d11b",
                            "title": "CTO Agent 实例化为独立 session",
                            "status": "active",
                            "parent_id": "project-a501",
                            "summary": "将CTO Agent配置为独立的OpenClaw会话",
                            "updated_at": "2026-03-18T09:31:36.294537+00:00"
                        }
                    ],
                    "updated_at": "2026-03-17T15:00:28.640104+00:00"
                }
            ],
            "tasks": [],
            "memories": [
                {
                    "id": "mem-001",
                    "content": "FounderOS focus on 末那识 rather than task management",
                    "layer": "judgment", 
                    "priority": "PP0",
                    "updated_at": "2026-03-19T10:00:00+00:00"
                }
            ],
            "stats": {
                "task_distribution": {"active": 1, "done": 14, "inbox": 34},
                "project_distribution": {"active": 3, "dropped": 1, "inbox": 3},
                "memory_distribution": {
                    "fact": {"PP0": 7, "PP1": 4},
                    "judgment": {"PP0": 12, "PP1": 1}, 
                    "scratch": {"PP1": 1, "PP2": 1}
                },
                "overview": {
                    "total_nodes": 58,
                    "total_goals": 2,
                    "total_projects": 7,
                    "total_tasks": 49,
                    "completed_tasks": 14,
                    "completion_rate": 28.6
                }
            },
            "recent_activity": [
                {
                    "id": "goal-ced834",
                    "title": "BinancePay", 
                    "status": "active",
                    "node_type": "goal",
                    "updated_at": "2026-03-19T06:48:44.700245+00:00"
                },
                {
                    "id": "project-4acae1",
                    "title": "BinancePay",
                    "status": "active",
                    "node_type": "project", 
                    "updated_at": "2026-03-19T06:48:06.661769+00:00"
                }
            ]
        }

if __name__ == "__main__":
    data = get_dashboard_data()
    print(json.dumps(data, indent=2, ensure_ascii=False))
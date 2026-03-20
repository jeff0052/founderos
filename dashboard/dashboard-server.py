#!/usr/bin/env python3
"""
FPMS Dashboard Local Server
启动本地服务器，提供实时数据更新的Dashboard
"""

import json
import os
import sqlite3
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import time

class DashboardHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.path = '/fpms-dashboard.html'
        elif self.path == '/api/data':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # 实时生成数据
            data = export_fpms_data()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
            return
            
        return super().do_GET()

def export_fpms_data():
    """实时导出FPMS数据"""
    try:
        db = sqlite3.connect('founderos/fpms/db/fpms.db')
        db.row_factory = sqlite3.Row
        
        # 基础统计
        goals = db.execute('SELECT COUNT(*) as count FROM nodes WHERE node_type = "goal"').fetchone()
        projects = db.execute('SELECT COUNT(*) as count FROM nodes WHERE node_type = "project"').fetchone()
        tasks = db.execute('SELECT COUNT(*) as count FROM nodes WHERE node_type = "task"').fetchone()
        
        # 任务状态分布
        task_status = db.execute('''
            SELECT status, COUNT(*) as count 
            FROM nodes 
            WHERE node_type = "task" 
            GROUP BY status
        ''').fetchall()
        
        task_dist = {ts['status']: ts['count'] for ts in task_status}
        completed = task_dist.get('done', 0)
        total_tasks = sum(task_dist.values())
        
        data = {
            "timestamp": datetime.now().isoformat(),
            "overview": {
                "goals": goals['count'],
                "projects": projects['count'], 
                "tasks": total_tasks,
                "completed": completed,
                "completion_rate": round(completed/total_tasks*100, 1) if total_tasks > 0 else 0
            },
            "task_distribution": task_dist
        }
        
        db.close()
        return data
        
    except Exception as e:
        return {"error": str(e), "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    PORT = 8080
    
    print(f"🚀 Starting FPMS Dashboard Server...")
    print(f"📊 Dashboard: http://localhost:{PORT}")
    print(f"📡 API: http://localhost:{PORT}/api/data")
    print(f"⏹️  Stop: Ctrl+C")
    print()
    
    os.chdir('/Users/jeff/.openclaw/workspace')
    
    try:
        with HTTPServer(('localhost', PORT), DashboardHandler) as server:
            print(f"✅ Server running on port {PORT}")
            server.serve_forever()
    except KeyboardInterrupt:
        print(f"\\n🛑 Dashboard server stopped")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Port {PORT} is already in use. Try: lsof -ti:{PORT} | xargs kill")
        else:
            print(f"❌ Error starting server: {e}")
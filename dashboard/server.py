#!/usr/bin/env python3
"""
FPMS Dashboard 服务器
提供静态文件和API数据服务
"""

import os
import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import mimetypes

# 添加当前目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    from api import get_dashboard_data
except ImportError:
    def get_dashboard_data():
        return {"error": "API module not available"}

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # API端点
        if path == '/api/data':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            try:
                data = get_dashboard_data()
                self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                error_data = {"error": str(e), "message": "Failed to get dashboard data"}
                self.wfile.write(json.dumps(error_data).encode('utf-8'))
            return
        
        # 静态文件服务
        if path == '/':
            path = '/index.html'
        elif path == '/detailed' or path == '/detailed/':
            path = '/detailed.html'
            
        file_path = current_dir + path
        
        if os.path.exists(file_path) and os.path.isfile(file_path):
            self.send_response(200)
            
            # 设置正确的 MIME 类型
            content_type, _ = mimetypes.guess_type(file_path)
            if content_type:
                self.send_header('Content-type', content_type)
            else:
                self.send_header('Content-type', 'text/plain')
                
            self.end_headers()
            
            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<h1>404 Not Found</h1><p>File not found: ' + path.encode() + b'</p>')

    def log_message(self, format, *args):
        # 简化日志输出
        print(f"[{self.address_string()}] {format % args}")

def run_server(port=8080):
    server_address = ('', port)
    httpd = HTTPServer(server_address, DashboardHandler)
    print(f"🌐 Dashboard server started at http://localhost:{port}")
    print(f"📊 Main Dashboard: http://localhost:{port}/")
    print(f"📈 Detailed Dashboard: http://localhost:{port}/detailed")
    print(f"🔌 API Data: http://localhost:{port}/api/data")
    print(f"\n按 Ctrl+C 停止服务器")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 服务器已停止")
        httpd.shutdown()

if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_server(port)
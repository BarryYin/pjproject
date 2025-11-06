#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的HTTP服务器，用于托管SIP Web客户端
"""

import http.server
import socketserver
import os
import sys

PORT = 8080

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # 添加CORS头，允许跨域
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

def main():
    # 切换到脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    print("=" * 60)
    print("SIP Web客户端服务器")
    print("=" * 60)
    print(f"\n服务器启动在端口: {PORT}")
    print(f"工作目录: {script_dir}")
    print(f"\n请在浏览器中打开:")
    print(f"  http://localhost:{PORT}/sip_web_client.html")
    print(f"\n或者从局域网访问:")
    print(f"  http://<服务器IP>:{PORT}/sip_web_client.html")
    print("\n按 Ctrl+C 停止服务器")
    print("=" * 60 + "\n")
    
    try:
        with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n服务器已停止")
        sys.exit(0)
    except OSError as e:
        if e.errno == 98:
            print(f"\n错误: 端口 {PORT} 已被占用")
            print("请尝试:")
            print(f"  1. 关闭占用端口的程序")
            print(f"  2. 或修改脚本中的 PORT 变量")
        else:
            print(f"\n错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试系统启动 - 找出卡在哪里
"""

import os
import sys
import time

print("="*70)
print("测试系统启动 - 逐步检查")
print("="*70)
print()

# 设置API Key - 使用环境变量（未设置则为空）
api_key = os.getenv('OPENAI_API_KEY', '')
if api_key:
    os.environ['OPENAI_API_KEY'] = api_key
else:
    print("⚠ OPENAI_API_KEY 未设置")
print()
print("1️⃣  测试导入...")
try:
    import pjsua as pj
    print("  ✓ pjsua")
except:
    print("  ✗ pjsua 导入失败")
    sys.exit(1)

try:
    from faster_whisper import WhisperModel
    print("  ✓ faster_whisper")
except:
    print("  ✗ faster_whisper")

try:
    import edge_tts
    print("  ✓ edge_tts")
except:
    print("  ✗ edge_tts")

print()

# 2. 测试Whisper加载
print("2️⃣  测试Whisper模型加载...")
start = time.time()
try:
    model = WhisperModel("base", device="cpu", compute_type="int8")
    elapsed = time.time() - start
    print(f"  ✓ 模型加载成功 ({elapsed:.2f}秒)")
except Exception as e:
    print(f"  ✗ 模型加载失败: {e}")

print()

# 3. 测试PJSIP初始化
print("3️⃣  测试PJSIP初始化...")
print("  创建库实例...")
try:
    lib = pj.Lib()
    print("  ✓ 库实例创建成功")
    
    print("  初始化...")
    start = time.time()
    lib.init(log_cfg=pj.LogConfig(level=1))
    elapsed = time.time() - start
    print(f"  ✓ 初始化成功 ({elapsed:.2f}秒)")
    
    print("  创建传输...")
    start = time.time()
    transport = lib.create_transport(pj.TransportType.UDP, pj.TransportConfig(0))
    elapsed = time.time() - start
    print(f"  ✓ 传输创建成功 ({elapsed:.2f}秒)")
    print(f"    地址: {transport.info().host}:{transport.info().port}")
    
    print("  启动库...")
    start = time.time()
    lib.start()
    elapsed = time.time() - start
    print(f"  ✓ 库启动成功 ({elapsed:.2f}秒)")
    
    print("  设置音频设备...")
    start = time.time()
    lib.set_null_snd_dev()
    elapsed = time.time() - start
    print(f"  ✓ 音频设备设置成功 ({elapsed:.2f}秒)")
    
    print("  销毁库...")
    lib.destroy()
    print("  ✓ 清理成功")
    
except Exception as e:
    print(f"  ✗ PJSIP初始化失败: {e}")
    import traceback
    traceback.print_exc()

print()

# 4. 测试HTTP服务器
print("4️⃣  测试HTTP服务器...")
try:
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import socket
    
    class TestHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        
        def log_message(self, format, *args):
            pass
    
    # 测试端口
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', 8090))
    sock.close()
    
    if result == 0:
        print("  ⚠ 端口8090已被占用")
    else:
        print("  ✓ 端口8090可用")
        
        print("  创建HTTP服务器...")
        server = HTTPServer(('0.0.0.0', 8090), TestHandler)
        print("  ✓ HTTP服务器创建成功")
        
        print("  测试服务3秒...")
        import threading
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        time.sleep(1)
        
        # 测试访问
        import urllib.request
        try:
            response = urllib.request.urlopen('http://localhost:8090/', timeout=2)
            print(f"  ✓ HTTP服务器响应正常: {response.read()}")
        except Exception as e:
            print(f"  ✗ HTTP服务器无响应: {e}")
        
        server.shutdown()
        print("  ✓ HTTP服务器关闭")

except Exception as e:
    print(f"  ✗ HTTP服务器测试失败: {e}")

print()
print("="*70)
print("测试完成")
print("="*70)

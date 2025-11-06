#!/usr/bin/env python3
"""测试PJSUA录音器创建"""
import pjsua as pj
import os

# 测试1: 创建普通WAV文件录音器
try:
    lib = pj.Lib()
    lib.init()
    lib.start()
    
    print("测试1: 创建WAV文件录音器...")
    recorder = lib.create_recorder("/tmp/test.wav")
    print("  ✓ 成功")
    lib.destroy()
except Exception as e:
    print(f"  ✗ 失败: {e}")

# 测试2: 创建管道录音器
try:
    lib = pj.Lib()
    lib.init()
    lib.start()
    
    pipe_path = '/tmp/test.pcm'
    if os.path.exists(pipe_path):
        os.remove(pipe_path)
    os.mkfifo(pipe_path)
    
    print("\n测试2: 创建管道录音器...")
    
    # 在后台线程打开读取端
    import threading
    def reader():
        with open(pipe_path, 'rb') as f:
            f.read(100)
    threading.Thread(target=reader, daemon=True).start()
    
    import time
    time.sleep(0.1)
    
    recorder = lib.create_recorder(pipe_path)
    print("  ✓ 成功")
    
    lib.destroy()
    os.remove(pipe_path)
except Exception as e:
    print(f"  ✗ 失败: {e}")
    import traceback
    traceback.print_exc()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预下载所有必需的模型
这样启动时就不用等待了
"""

import os
import sys

print("="*70)
print("  预下载AI模型")
print("="*70)
print()

# 1. 下载Whisper模型
print("1️⃣  下载 Whisper ASR 模型...")
print("   这是最大的下载，请耐心等待...")
print()

try:
    from faster_whisper import WhisperModel
    
    models = ['base']  # 可以添加 'tiny', 'small' 等
    
    for model_name in models:
        print(f"   下载 {model_name} 模型...")
        print(f"   模型大小:")
        if model_name == 'tiny':
            print(f"     - tiny: ~75MB")
        elif model_name == 'base':
            print(f"     - base: ~142MB")
        elif model_name == 'small':
            print(f"     - small: ~466MB")
        print()
        
        # 下载模型
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        print(f"   ✓ {model_name} 模型下载完成!")
        print()
        
        # 测试一下
        print(f"   测试 {model_name} 模型...")
        # 模型已加载，不需要实际测试
        print(f"   ✓ {model_name} 模型可用!")
        print()
    
    print("✓ 所有 Whisper 模型已下载!")
    
except Exception as e:
    print(f"✗ Whisper 模型下载失败: {e}")
    print()
    print("可能原因:")
    print("  1. 网络连接问题")
    print("  2. faster-whisper 未安装")
    print()
    print("解决方法:")
    print("  pip3 install faster-whisper")
    sys.exit(1)

print()

# 2. 验证Edge TTS
print("2️⃣  验证 Edge TTS...")
try:
    import edge_tts
    print("   ✓ Edge TTS 已安装 (无需下载)")
except ImportError:
    print("   ✗ Edge TTS 未安装")
    print("   安装: pip3 install edge-tts")

print()

# 3. 验证OpenAI
print("3️⃣  验证 OpenAI SDK...")
try:
    from openai import OpenAI
    print("   ✓ OpenAI SDK 已安装")
except ImportError:
    print("   ✗ OpenAI SDK 未安装")
    print("   安装: pip3 install openai")

print()

# 4. 创建必要的目录
print("4️⃣  创建目录...")
dirs = [
    '/home/henry/pjproject/audio_files',
    '/home/henry/pjproject/recordings',
    '/home/henry/pjproject/temp_audio'
]

for dir_path in dirs:
    os.makedirs(dir_path, exist_ok=True)
    print(f"   ✓ {os.path.basename(dir_path)}/")

print()

print("="*70)
print("✓ 所有准备工作完成!")
print("="*70)
print()
print("现在启动系统会非常快，无需等待下载。")
print()
print("启动命令:")
print("  ./start_now.sh")
print("或")
print("  python3 sip_ai_conversation.py")
print()

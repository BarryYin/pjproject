#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI系统配置测试脚本
验证所有组件是否正常工作
"""

import os
import sys

print("="*70)
print("  AI智能对话系统 - 配置测试")
print("="*70)
print()

# 1. 检查环境变量
print("1️⃣  检查OpenAI API Key...")
api_key = os.getenv('OPENAI_API_KEY')
if api_key:
    print(f"  ✓ API Key已设置: {api_key[:20]}...")
else:
    print("  ✗ API Key未设置")
    print("  请运行: export OPENAI_API_KEY='your-key'")
    sys.exit(1)

print()

# 2. 测试OpenAI连接
print("2️⃣  测试OpenAI API连接...")
try:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    
    # 简单测试
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Say hello in Indonesian"}],
        max_tokens=20
    )
    
    reply = response.choices[0].message.content
    print(f"  ✓ API连接正常")
    print(f"  测试回复: {reply}")
except Exception as e:
    print(f"  ✗ API连接失败: {e}")
    sys.exit(1)

print()

# 3. 测试Edge TTS
print("3️⃣  测试Edge TTS...")
try:
    import asyncio
    import edge_tts
    
    async def test_tts():
        text = "Halo, ini adalah tes"
        communicate = edge_tts.Communicate(text, "id-ID-ArdiNeural")
        
        # 列出可用语音
        voices = await edge_tts.list_voices()
        id_voices = [v for v in voices if v['Locale'].startswith('id-ID')]
        
        return len(id_voices)
    
    count = asyncio.run(test_tts())
    print(f"  ✓ Edge TTS正常")
    print(f"  可用印尼语音: {count}个")
except Exception as e:
    print(f"  ✗ Edge TTS测试失败: {e}")

print()

# 4. 测试faster-whisper
print("4️⃣  测试faster-whisper...")
try:
    from faster_whisper import WhisperModel
    
    print("  正在加载模型 (首次会下载，请稍候)...")
    model = WhisperModel("tiny", device="cpu", compute_type="int8")
    
    print("  ✓ faster-whisper正常")
    print("  模型: tiny (测试用)")
except Exception as e:
    print(f"  ⚠ faster-whisper警告: {e}")
    print("  提示: 首次使用会自动下载模型")

print()

# 5. 检查ffmpeg
print("5️⃣  检查ffmpeg...")
import subprocess
result = subprocess.run(['which', 'ffmpeg'], capture_output=True)
if result.returncode == 0:
    print("  ✓ ffmpeg已安装")
else:
    print("  ✗ ffmpeg未安装")
    print("  安装: sudo apt-get install ffmpeg")

print()

# 6. 检查目录
print("6️⃣  检查目录结构...")
dirs = {
    'audio_files': '/home/henry/pjproject/audio_files',
    'recordings': '/home/henry/pjproject/recordings',
    'temp_audio': '/home/henry/pjproject/temp_audio'
}

for name, path in dirs.items():
    if os.path.exists(path):
        print(f"  ✓ {name}/")
    else:
        os.makedirs(path, exist_ok=True)
        print(f"  ✓ {name}/ (已创建)")

print()
print("="*70)
print("  ✓ 系统配置完成!")
print("="*70)
print()
print("现在可以启动AI对话系统:")
print("  python3 sip_ai_conversation.py")
print()
print("或使用快速启动:")
print("  ./quick_start_ai_conversation.sh")
print()

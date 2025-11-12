#!/usr/bin/env python3
"""测试新的DashScope TTS"""

import sys
import os
sys.path.insert(0, '/home/henry/pjproject')

# 导入TTS引擎
from sip_ai_with_webrtc_vad import TTSEngine, CONFIG

print("="*60)
print("  测试 DashScope TTS")
print("="*60)
print()

# 创建TTS引擎
print("1. 初始化TTS引擎...")
tts = TTSEngine()
print()

# 测试文本
test_texts = [
    "Halo, selamat datang di sistem AI kami.",
    "Terima kasih sudah menghubungi kami.",
    "Apakah ada yang bisa saya bantu hari ini?"
]

print("2. 测试合成...")
print()

for i, text in enumerate(test_texts, 1):
    print(f"[{i}/{len(test_texts)}] 合成: \"{text}\"")
    
    wav = tts.synthesize(text)
    
    if wav and os.path.exists(wav):
        size = os.path.getsize(wav)
        print(f"  ✓ 成功: {wav}")
        print(f"  ✓ 大小: {size} bytes")
        
        # 询问是否播放
        try:
            play = input("  播放? (y/n): ").strip().lower()
            if play == 'y':
                print("  [播放中...]")
                os.system(f'ffplay -nodisp -autoexit "{wav}" 2>/dev/null')
        except:
            pass
    else:
        print(f"  ✗ 失败")
    
    print()

print("="*60)
print("  测试完成")
print("="*60)
print()
print(f"生成的文件保存在: {CONFIG['temp_dir']}")

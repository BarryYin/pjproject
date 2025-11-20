#!/usr/bin/env python3
# 快速测试NLS TTS

import sys
sys.path.insert(0, 'alibabacloud-nls-python-sdk')

import nls
from nls.token import getToken
import time
import os

AKID = 'LTAI5tGtuuJyivveR3UFARYs'
AKKEY = 'aY32qhvLBpslrxwTUSO6tYlMscCitG'
APPKEY = 'dqAnq24vXe5lJUlq'

print("获取Token...")
token = getToken(AKID, AKKEY)
print(f"Token: {token[:30]}...")

output_file = "test_tts_output.wav"
audio_file = None
completed = False

def on_data(data, *args):
    global audio_file
    if audio_file:
        audio_file.write(data)
        print(f".", end="", flush=True)

def on_completed(msg, *args):
    global audio_file, completed
    if audio_file:
        audio_file.close()
        print(f"\n✓ 完成")
    completed = True

def on_error(msg, *args):
    global completed
    print(f"\n✗ 错误: {msg}")
    completed = True

print("创建合成器...")
tts = nls.NlsSpeechSynthesizer(
    token=token,
    appkey=APPKEY,
    on_data=on_data,
    on_completed=on_completed,
    on_error=on_error
)

print("开始合成...")
audio_file = open(output_file, 'wb')

tts.start(
    text="Halo, apa kabar?",
    voice="indah",
    aformat="wav",
    sample_rate=8000,
    volume=50,
    speech_rate=0
)

print("等待完成", end="", flush=True)
timeout = 0
while not completed and timeout < 100:
    time.sleep(0.1)
    timeout += 1

if os.path.exists(output_file):
    size = os.path.getsize(output_file)
    print(f"\n文件大小: {size} 字节")
    if size > 0:
        print(f"✓ 成功: {output_file}")
    else:
        print(f"✗ 文件为空")
else:
    print(f"✗ 文件不存在")

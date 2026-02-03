#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试阿里云语音合成(TTS)功能"""

import sys
import os

# 添加SDK路径
sys.path.insert(0, '/home/henry/pjproject/alibabacloud-nls-python-sdk')

import nls
from nls.token import getToken

# 配置信息
# 使用环境变量加载凭证
import os
AKID = os.getenv('ALI_NLS_AKID', '')
AKKEY = os.getenv('ALI_NLS_AKKEY', '')
APPKEY = os.getenv('ALI_NLS_APPKEY', '')

# 测试文本
TEST_TEXT = "Selamat pagi RISSA S.E pinjaman Anda sebesar 970200.0 akan segera jatuh tempo."

def get_token():
    """获取访问token"""
    print("正在获取访问token...")
    try:
        token = getToken(AKID, AKKEY)
        print(f"Token获取成功: {token[:20]}...")
        return token
    except Exception as e:
        print(f"获取token失败: {e}")
        import traceback
        traceback.print_exc()
        return None

class TTSTest:
    def __init__(self, output_file):
        self.output_file = output_file
        self.audio_file = None
        
    def on_metainfo(self, message, *args):
        print(f"[元信息] {message}")  

    def on_error(self, message, *args):
        print(f"[错误] {message}")

    def on_close(self, *args):
        print("[连接关闭]")
        if self.audio_file:
            try:
                self.audio_file.close()
                print(f"音频已保存到: {self.output_file}")
            except Exception as e:
                print(f"关闭文件失败: {e}")

    def on_data(self, data, *args):
        if self.audio_file:
            try:
                self.audio_file.write(data)
            except Exception as e:
                print(f"写入数据失败: {e}")

    def on_completed(self, message, *args):
        print(f"[合成完成] {message}")

    def run(self, text, token):
        print("=" * 60)
        print("开始测试阿里云TTS...")
        print(f"要合成的文本: {text}")
        print("=" * 60)
        
        try:
            self.audio_file = open(self.output_file, "wb")
            
            tts = nls.NlsSpeechSynthesizer(
                token=token,
                appkey=APPKEY,
                long_tts=False,
                on_metainfo=self.on_metainfo,
                on_data=self.on_data,
                on_completed=self.on_completed,
                on_error=self.on_error,
                on_close=self.on_close
            )

            print("\n正在合成语音...")
            tts.start(
                text=text,
                voice="indah",  # 印尼语女声
                aformat="wav",
                sample_rate=16000
            )
            
            print("\nTTS合成完成!")
            return True
            
        except Exception as e:
            print(f"\n发生异常: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    nls.enableTrace(True)
    
    # 获取token
    token = get_token()
    if not token:
        print("\n✗ 无法获取token，测试终止!")
        sys.exit(1)
    
    output_file = "/home/henry/pjproject/test_alibaba_tts_output.wav"
    tts_test = TTSTest(output_file)
    
    success = tts_test.run(TEST_TEXT, token)
    
    if success and os.path.exists(output_file):
        file_size = os.path.getsize(output_file)
        print(f"\n✓ TTS测试成功!")
        print(f"  文件大小: {file_size} 字节")
        print(f"  可以用以下命令播放:")
        print(f"  ffplay {output_file}")
    else:
        print("\n✗ TTS测试失败!")
        sys.exit(1)

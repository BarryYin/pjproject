#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试阿里云语音识别(ASR)功能"""

import sys
import os
import time

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

class ASRTest:
    def __init__(self):
        self.recognition_result = None
        self.error_message = None
        
    def on_start(self, message, *args):
        print(f"[识别开始] {message}")

    def on_error(self, message, *args):
        print(f"[错误] {message}")
        self.error_message = message

    def on_close(self, *args):
        print("[连接关闭]")

    def on_result_changed(self, message, *args):
        print(f"[中间结果] {message}")

    def on_completed(self, message, *args):
        print(f"[识别完成] {message}")
        self.recognition_result = message

    def run(self, audio_file, token):
        print("=" * 60)
        print("开始测试阿里云ASR...")
        print(f"音频文件: {audio_file}")
        print("=" * 60)
        
        if not os.path.exists(audio_file):
            print(f"\n错误: 音频文件不存在: {audio_file}")
            return False
            
        try:
            # 读取音频文件
            with open(audio_file, 'rb') as f:
                audio_data = f.read()
            
            print(f"音频文件大小: {len(audio_data)} 字节")
            
            sr = nls.NlsSpeechRecognizer(
                token=token,
                appkey=APPKEY,
                on_start=self.on_start,
                on_result_changed=self.on_result_changed,
                on_completed=self.on_completed,
                on_error=self.on_error,
                on_close=self.on_close
            )

            print("\n开始识别...")
            sr.start(
                aformat="pcm",
                sample_rate=16000,
                enable_intermediate_result=True,
                enable_punctuation_prediction=True,
                enable_inverse_text_normalization=True
            )
            
            # 分片发送音频数据
            chunk_size = 640  # 16k采样率, 单声道, 16bit, 20ms
            slices = [audio_data[i:i+chunk_size] for i in range(0, len(audio_data), chunk_size)]
            
            print(f"分 {len(slices)} 片发送音频数据...")
            for chunk in slices:
                sr.send_audio(chunk)
                time.sleep(0.01)  # 模拟实时音频流
            
            print("音频发送完毕，等待识别结果...")
            sr.stop()
            
            print("\nASR识别完成!")
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
    
    # 使用SDK自带的测试音频文件
    test_audio = "/home/henry/pjproject/alibabacloud-nls-python-sdk/tests/test1.pcm"
    
    asr_test = ASRTest()
    success = asr_test.run(test_audio, token)
    
    if success and asr_test.recognition_result:
        print(f"\n✓ ASR测试成功!")
        print(f"  识别结果: {asr_test.recognition_result}")
    else:
        print("\n✗ ASR测试失败!")
        if asr_test.error_message:
            print(f"  错误信息: {asr_test.error_message}")
        sys.exit(1)

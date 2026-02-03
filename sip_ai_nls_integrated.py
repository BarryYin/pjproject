#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI对话系统 - 阿里云NLS WebSocket完整集成版
ASR: 阿里云NLS实时语音识别 (WebSocket)
TTS: 阿里云NLS语音合成 (WebSocket)
AI: OpenAI GPT-3.5-turbo
VAD: WebRTC VAD

特性:
- 使用阿里云NLS WebSocket实现低延迟ASR/TTS
- WebRTC VAD实时语音检测
- OpenAI智能对话
- 双向录音
- Web控制界面
"""

import sys
import time
import pjsua as pj
import threading
import os
import json
import queue
import wave
import webrtcvad
from datetime import datetime
from collections import deque
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# 添加阿里云NLS SDK路径
sys.path.insert(0, '/home/henry/pjproject/alibabacloud-nls-python-sdk')
import nls
from nls.token import getToken

# ==================== 配置 ====================

CONFIG = {
    # SIP配置
    'server': '147.139.205.88',
    'port': 5060,
    'caller_number': '6281479242434',
    'prefix': '13462',
    'log_level': 3,
    
    # 目录配置
    'audio_dir': '/home/henry/pjproject/audio_files',
    'recordings_dir': '/home/henry/pjproject/recordings',
    'temp_dir': '/home/henry/pjproject/temp_audio',
    
    # API配置
    'api_host': '0.0.0.0',
    'api_port': 8090,
    
    # 阿里云NLS配置
    # 阿里云NLS配置 - 使用环境变量
    'nls_akid': os.getenv('ALI_NLS_AKID', ''),
    'nls_akkey': os.getenv('ALI_NLS_AKKEY', ''),
    'nls_appkey': os.getenv('ALI_NLS_APPKEY', ''),
    'nls_tts_voice': 'indah',  # 印尼语女声
    
    # OpenAI配置
    'openai_api_key': os.getenv('OPENAI_API_KEY', ''),
    'ai_model': 'gpt-3.5-turbo',
    'ai_language': 'id',  # 印尼语
    
    # WebRTC VAD配置
    'vad_aggressiveness': 2,
    'vad_frame_duration': 30,
    'vad_silence_frames': 20,
    'vad_min_speech_frames': 5,
}

for d in [CONFIG['temp_dir'], CONFIG['recordings_dir'], CONFIG['audio_dir']]:
    os.makedirs(d, exist_ok=True)


# ==================== WebRTC VAD检测器 ====================

class WebRTCVADDetector:
    """使用WebRTC VAD的语音检测器"""
    
    def __init__(self, aggressiveness=2, frame_duration=30):
        self.vad = webrtcvad.Vad(aggressiveness)
        self.frame_duration = frame_duration
        self.sample_rate = 8000
        self.frame_size = int(self.sample_rate * self.frame_duration / 1000) * 2
        
        self.is_speaking = False
        self.speech_frames = []
        self.silence_count = 0
        
        self.silence_threshold = CONFIG['vad_silence_frames']
        self.min_speech_frames = CONFIG['vad_min_speech_frames']
        
        print(f"[VAD] WebRTC VAD初始化 (激进度:{aggressiveness}, 帧长:{frame_duration}ms)")
    
    def process_audio(self, audio_data):
        """处理音频数据，返回完整句子或None"""
        offset = 0
        
        while offset + self.frame_size <= len(audio_data):
            frame = audio_data[offset:offset + self.frame_size]
            
            try:
                is_speech = self.vad.is_speech(frame, self.sample_rate)
                
                if is_speech:
                    if not self.is_speaking:
                        self.is_speaking = True
                        print("[VAD] >>> 检测到说话")
                    
                    self.speech_frames.append(frame)
                    self.silence_count = 0
                else:
                    if self.is_speaking:
                        self.silence_count += 1
                        self.speech_frames.append(frame)
                        
                        if self.silence_count >= self.silence_threshold:
                            if len(self.speech_frames) >= self.min_speech_frames:
                                print(f"[VAD] <<< 句子结束 ({len(self.speech_frames)}帧)")
                                speech_audio = b''.join(self.speech_frames)
                                self.reset()
                                return ('speech_complete', speech_audio)
                            else:
                                self.reset()
                
            except Exception as e:
                print(f"[VAD] 处理错误: {e}")
            
            offset += self.frame_size
        
        return None
    
    def reset(self):
        self.is_speaking = False
        self.speech_frames = []
        self.silence_count = 0


# ==================== 阿里云NLS ASR引擎 (WebSocket) ====================

class NLSASREngine:
    """阿里云NLS实时语音识别引擎"""
    
    def __init__(self):
        self.token = None
        self.appkey = CONFIG['nls_appkey']
        print("[ASR] 初始化阿里云NLS ASR引擎...")
    
    def get_token(self):
        """获取访问token"""
        if not self.token:
            try:
                print("[ASR] 正在获取token...")
                self.token = getToken(CONFIG['nls_akid'], CONFIG['nls_akkey'])
                print(f"[ASR] Token获取成功: {self.token[:20]}...")
            except Exception as e:
                print(f"[ASR] Token获取失败: {e}")
                return False
        return True
    
    def transcribe(self, audio_file):
        """识别音频文件（一句话识别）"""
        if not self.get_token():
            return ""
        
        try:
            print(f"[ASR] 开始识别: {os.path.basename(audio_file)}")
            start_time = time.time()
            
            # 读取音频数据
            with open(audio_file, 'rb') as f:
                audio_data = f.read()
            
            # 创建识别结果容器
            result_container = {'text': '', 'completed': False, 'error': None}
            lock = threading.Lock()
            condition = threading.Condition(lock)
            
            def on_completed(message, *args):
                with condition:
                    try:
                        msg = json.loads(message)
                        if 'payload' in msg and 'result' in msg['payload']:
                            result_container['text'] = msg['payload']['result']
                    except:
                        pass
                    result_container['completed'] = True
                    condition.notify()
            
            def on_error(message, *args):
                with condition:
                    result_container['error'] = message
                    result_container['completed'] = True
                    condition.notify()
            
            def on_close(*args):
                with condition:
                    if not result_container['completed']:
                        result_container['completed'] = True
                        condition.notify()
            
            # 创建识别器
            sr = nls.NlsSpeechRecognizer(
                token=self.token,
                appkey=self.appkey,
                on_completed=on_completed,
                on_error=on_error,
                on_close=on_close
            )
            
            # 开始识别
            sr.start(
                aformat="pcm",
                sample_rate=8000,
                enable_intermediate_result=False,
                enable_punctuation_prediction=True,
                enable_inverse_text_normalization=True
            )
            
            # 发送音频数据（分片）
            chunk_size = 640  # 8k采样率, 20ms
            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i:i+chunk_size]
                sr.send_audio(chunk)
                time.sleep(0.01)
            
            # 停止识别
            sr.stop()
            
            # 等待结果（最多10秒）
            with condition:
                condition.wait(timeout=10)
            
            elapsed = time.time() - start_time
            text = result_container.get('text', '').strip()
            
            if text:
                print(f"[ASR] ✓ 识别成功: '{text}' ({elapsed:.1f}s)")
            else:
                print(f"[ASR] ✗ 识别失败或无结果 ({elapsed:.1f}s)")
            
            return text
            
        except Exception as e:
            print(f"[ASR] 识别异常: {e}")
            import traceback
            traceback.print_exc()
            return ""


# ==================== 阿里云NLS TTS引擎 (WebSocket) ====================

class NLSTTSEngine:
    """阿里云NLS语音合成引擎"""
    
    def __init__(self):
        self.token = None
        self.appkey = CONFIG['nls_appkey']
        self.voice = CONFIG['nls_tts_voice']
        print(f"[TTS] 初始化阿里云NLS TTS引擎 (发音人:{self.voice})...")
    
    def get_token(self):
        """获取访问token"""
        if not self.token:
            try:
                print("[TTS] 正在获取token...")
                self.token = getToken(CONFIG['nls_akid'], CONFIG['nls_akkey'])
                print(f"[TTS] Token获取成功: {self.token[:20]}...")
            except Exception as e:
                print(f"[TTS] Token获取失败: {e}")
                return False
        return True
    
    def synthesize(self, text):
        """合成语音"""
        if not text or not text.strip():
            return None
        
        if not self.get_token():
            return None
        
        try:
            print(f"[TTS] 开始合成: '{text[:30]}...'")
            start_time = time.time()
            
            # 生成输出文件路径
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            output_file = os.path.join(CONFIG['temp_dir'], f"tts_nls_{ts}.wav")
            
            # 创建合成结果容器
            result_container = {'completed': False, 'error': None, 'file': output_file}
            lock = threading.Lock()
            condition = threading.Condition(lock)
            audio_file = None
            
            def on_data(data, *args):
                nonlocal audio_file
                try:
                    if audio_file is None:
                        audio_file = open(output_file, 'wb')
                    audio_file.write(data)
                except Exception as e:
                    print(f"[TTS] 写入数据失败: {e}")
            
            def on_completed(message, *args):
                nonlocal audio_file
                with condition:
                    if audio_file:
                        try:
                            audio_file.close()
                        except:
                            pass
                    result_container['completed'] = True
                    condition.notify()
            
            def on_error(message, *args):
                nonlocal audio_file
                with condition:
                    if audio_file:
                        try:
                            audio_file.close()
                        except:
                            pass
                    result_container['error'] = message
                    result_container['completed'] = True
                    condition.notify()
            
            def on_close(*args):
                nonlocal audio_file
                with condition:
                    if audio_file:
                        try:
                            audio_file.close()
                        except:
                            pass
                    if not result_container['completed']:
                        result_container['completed'] = True
                        condition.notify()
            
            # 创建合成器
            tts = nls.NlsSpeechSynthesizer(
                token=self.token,
                appkey=self.appkey,
                on_data=on_data,
                on_completed=on_completed,
                on_error=on_error,
                on_close=on_close
            )
            
            # 开始合成
            tts.start(
                text=text,
                voice=self.voice,
                aformat="wav",
                sample_rate=8000,
                volume=50,
                speech_rate=0
            )
            
            # 等待完成（最多30秒）
            with condition:
                condition.wait(timeout=30)
            
            elapsed = time.time() - start_time
            
            # 检查结果
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                size = os.path.getsize(output_file)
                print(f"[TTS] ✓ 合成成功: {size}字节 ({elapsed:.1f}s)")
                return output_file
            else:
                print(f"[TTS] ✗ 合成失败 ({elapsed:.1f}s)")
                return None
            
        except Exception as e:
            print(f"[TTS] 合成异常: {e}")
            import traceback
            traceback.print_exc()
            return None


# ==================== AI对话引擎 ====================

class DialogueEngine:
    """AI对话引擎 (OpenAI)"""
    
    def __init__(self):
        self.conversation_history = []
        self.system_prompt = f"""You are a helpful AI assistant speaking in Indonesian.
Keep responses concise and natural (1-2 sentences).
You are having a phone conversation, so be conversational and friendly."""
        
        print(f"[AI] 初始化 {CONFIG['ai_model']} 对话引擎")
        
        if not CONFIG['openai_api_key']:
            print("[AI] ⚠ 警告: 未设置 OPENAI_API_KEY")
    
    def get_response(self, user_input):
        """获取AI回复"""
        if not CONFIG['openai_api_key']:
            return "Maaf, saya tidak dapat menjawab sekarang."
        
        try:
            print(f"[AI] 用户: '{user_input}'")
            start_time = time.time()
            
            from openai import OpenAI
            client = OpenAI(api_key=CONFIG['openai_api_key'])
            
            # 构建消息
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(self.conversation_history[-6:])  # 最近3轮对话
            messages.append({"role": "user", "content": user_input})
            
            # 调用API
            response = client.chat.completions.create(
                model=CONFIG['ai_model'],
                messages=messages,
                max_tokens=150,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content.strip()
            elapsed = time.time() - start_time
            
            # 保存对话历史
            self.conversation_history.append({"role": "user", "content": user_input})
            self.conversation_history.append({"role": "assistant", "content": ai_response})
            
            print(f"[AI] 回复: '{ai_response}' ({elapsed:.1f}s)")
            return ai_response
            
        except Exception as e:
            print(f"[AI] 错误: {e}")
            return "Maaf, terjadi kesalahan."


# ==================== 实时录音文件读取器 ====================

class RealtimeWavReader:
    """实时读取录音文件的新数据"""
    
    def __init__(self, filename):
        self.filename = filename
        self.last_pos = 0
    
    def read_new_data(self):
        """读取新增的数据"""
        try:
            file_size = os.path.getsize(self.filename)
            if file_size > self.last_pos:
                with open(self.filename, 'rb') as f:
                    f.seek(self.last_pos)
                    new_data = f.read(file_size - self.last_pos)
                    self.last_pos = file_size
                    return new_data
        except Exception as e:
            pass
        return b''


# ==================== AI对话回调处理 ====================

class AIConversationCallback(pj.CallCallback):
    """AI对话呼叫回调"""
    
    def __init__(self, call=None):
        pj.CallCallback.__init__(self, call)
        self.connected = False
        self.lock = threading.Lock()
        
        # VAD和音频处理
        self.vad = WebRTCVADDetector(
            CONFIG['vad_aggressiveness'],
            CONFIG['vad_frame_duration']
        )
        self.wav_reader = None
        self.vad_thread = None
        self.vad_running = False
        
        # 组件
        self.asr = NLSASREngine()
        self.tts = NLSTTSEngine()
        self.dialogue = DialogueEngine()
        
        # 录音
        self.recorder = None
        self.recorder_id = None
        self.record_file = None
        
        print("[回调] AI对话回调初始化完成")
    
    def on_state(self):
        """呼叫状态变化"""
        try:
            info = self.call.info()
            print(f"\n[状态] {info.state_text} - {info.last_code}")
            
            if info.state == pj.CallState.CONFIRMED:
                with self.lock:
                    self.connected = True
                print("[状态] >>> 通话已接通，启动AI对话系统")
                self.start_vad_recording()
                
            elif info.state == pj.CallState.DISCONNECTED:
                with self.lock:
                    self.connected = False
                print("[状态] >>> 通话已结束")
                self.stop_vad_recording()
        except Exception as e:
            print(f"[错误] 状态回调异常: {e}")
    
    def on_media_state(self):
        """媒体状态变化"""
        try:
            info = self.call.info()
            if info.media_state == pj.MediaState.ACTIVE:
                call_slot = info.conf_slot
                pj.Lib.instance().conf_connect(call_slot, 0)
                pj.Lib.instance().conf_connect(0, call_slot)
                print("[媒体] 双向音频通道已激活")
        except Exception as e:
            print(f"[错误] 媒体回调异常: {e}")
    
    def start_vad_recording(self):
        """开始VAD录音"""
        try:
            info = self.call.info()
            
            # 创建录音文件
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.record_file = os.path.join(CONFIG['recordings_dir'], f"call_nls_{ts}.wav")
            
            # 创建录音器
            self.recorder = pj.Lib.instance().create_recorder(self.record_file)
            self.recorder_id = pj.Lib.instance().recorder_get_slot(self.recorder)
            
            # 连接音频到录音器（只录对方的声音）
            call_slot = info.conf_slot
            pj.Lib.instance().conf_connect(call_slot, self.recorder_id)
            
            print(f"[录音] 开始录音: {self.record_file}")
            
            # 创建实时读取器
            self.wav_reader = RealtimeWavReader(self.record_file)
            
            # 启动VAD处理线程
            self.vad_running = True
            self.vad_thread = threading.Thread(target=self.vad_process_loop, daemon=True)
            self.vad_thread.start()
            
        except Exception as e:
            print(f"[错误] 启动录音失败: {e}")
            import traceback
            traceback.print_exc()
    
    def stop_vad_recording(self):
        """停止VAD录音"""
        try:
            # 停止VAD线程
            self.vad_running = False
            if self.vad_thread:
                self.vad_thread.join(timeout=2)
            
            # 停止录音
            if self.recorder_id is not None:
                try:
                    pj.Lib.instance().conf_disconnect(
                        self.call.info().conf_slot, 
                        self.recorder_id
                    )
                except:
                    pass
            
            if self.recorder:
                try:
                    pj.Lib.instance().recorder_destroy(self.recorder)
                except:
                    pass
            
            print(f"[录音] 已停止，文件: {self.record_file}")
            
        except Exception as e:
            print(f"[错误] 停止录音失败: {e}")
    
    def vad_process_loop(self):
        """VAD处理主循环"""
        print("[VAD] 处理循环启动")
        
        last_read_time = time.time()
        read_interval = 0.1  # 每100ms读取一次
        
        while self.vad_running:
            try:
                current_time = time.time()
                
                # 定时读取新音频数据
                if current_time - last_read_time >= read_interval:
                    new_data = self.wav_reader.read_new_data()
                    last_read_time = current_time
                    
                    if new_data:
                        # 跳过WAV头（前44字节）
                        if self.wav_reader.last_pos <= 44:
                            continue
                        
                        # VAD处理
                        result = self.vad.process_audio(new_data)
                        
                        if result and result[0] == 'speech_complete':
                            audio_data = result[1]
                            self.process_speech(audio_data)
                
                time.sleep(0.05)
                
            except Exception as e:
                print(f"[VAD] 循环错误: {e}")
                time.sleep(0.5)
        
        print("[VAD] 处理循环已停止")
    
    def process_speech(self, audio_data):
        """处理检测到的语音片段"""
        try:
            # 保存音频片段
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            speech_file = os.path.join(CONFIG['temp_dir'], f"speech_{ts}.wav")
            
            with wave.open(speech_file, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(8000)
                wf.writeframes(audio_data)
            
            print(f"[处理] 保存语音: {os.path.basename(speech_file)} ({len(audio_data)}字节)")
            
            # ASR识别
            text = self.asr.transcribe(speech_file)
            
            if text:
                # AI回复
                response = self.dialogue.get_response(text)
                
                if response:
                    # TTS合成
                    tts_file = self.tts.synthesize(response)
                    
                    if tts_file:
                        # 播放语音
                        self.play_audio_response(tts_file)
            
        except Exception as e:
            print(f"[错误] 处理语音失败: {e}")
            import traceback
            traceback.print_exc()
    
    def play_audio_response(self, audio_file):
        """播放AI语音回复"""
        try:
            print(f"[播放] 开始播放: {os.path.basename(audio_file)}")
            
            player = pj.Lib.instance().create_player(audio_file, loop=False)
            player_slot = pj.Lib.instance().player_get_slot(player)
            
            # 连接到通话
            info = self.call.info()
            pj.Lib.instance().conf_connect(player_slot, info.conf_slot)
            
            # 等待播放完成
            while pj.Lib.instance().player_get_pos(player) >= 0:
                time.sleep(0.1)
                if not self.connected:
                    break
            
            # 清理
            pj.Lib.instance().conf_disconnect(player_slot, info.conf_slot)
            pj.Lib.instance().player_destroy(player)
            
            print("[播放] 播放完成")
            
        except Exception as e:
            print(f"[错误] 播放失败: {e}")


# ==================== PJSUA账户回调 ====================

class MyAccountCallback(pj.AccountCallback):
    def __init__(self, account=None):
        pj.AccountCallback.__init__(self, account)
    
    def on_incoming_call(self, call):
        print(f"\n[来电] {call.info().remote_uri}")
        call.set_callback(AIConversationCallback(call))
        call.answer(200)


# ==================== HTTP API服务器 ====================

current_call = None
call_lock = threading.Lock()

class APIHandler(BaseHTTPRequestHandler):
    """HTTP API处理器"""
    
    def log_message(self, format, *args):
        pass  # 禁用日志
    
    def do_GET(self):
        """处理GET请求"""
        parsed = urlparse(self.path)
        
        if parsed.path == '/':
            self.serve_web_interface()
        elif parsed.path == '/status':
            self.handle_status()
        else:
            self.send_error(404)
    
    def do_POST(self):
        """处理POST请求"""
        parsed = urlparse(self.path)
        
        if parsed.path == '/call':
            self.handle_call()
        elif parsed.path == '/hangup':
            self.handle_hangup()
        else:
            self.send_error(404)
    
    def serve_web_interface(self):
        """提供Web界面"""
        html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>AI对话系统 - 阿里云NLS版</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            max-width: 800px; 
            margin: 50px auto; 
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 { 
            color: #333; 
            text-align: center;
            margin-bottom: 10px;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }
        .tech-stack {
            background: #e3f2fd;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            font-size: 13px;
        }
        .tech-stack strong { color: #1976d2; }
        input { 
            width: 100%; 
            padding: 12px; 
            margin: 10px 0; 
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
            box-sizing: border-box;
        }
        button { 
            width: 100%; 
            padding: 15px; 
            margin: 10px 0; 
            font-size: 16px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            transition: background 0.3s;
        }
        .btn-call { 
            background: #4CAF50; 
            color: white; 
        }
        .btn-call:hover { background: #45a049; }
        .btn-call:disabled { 
            background: #ccc; 
            cursor: not-allowed; 
        }
        .btn-hangup { 
            background: #f44336; 
            color: white; 
        }
        .btn-hangup:hover { background: #da190b; }
        .btn-hangup:disabled { 
            background: #ccc; 
            cursor: not-allowed; 
        }
        #status { 
            padding: 15px; 
            margin: 20px 0; 
            border-radius: 5px;
            text-align: center;
            font-weight: bold;
        }
        .status-idle { background: #fff3cd; color: #856404; }
        .status-calling { background: #d1ecf1; color: #0c5460; }
        .status-connected { background: #d4edda; color: #155724; }
        .info {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-top: 20px;
            font-size: 13px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 AI对话系统</h1>
        <div class="subtitle">阿里云NLS WebSocket完整集成版</div>
        
        <div class="tech-stack">
            <strong>技术栈:</strong><br>
            • ASR: 阿里云NLS实时识别 (WebSocket)<br>
            • TTS: 阿里云NLS语音合成 (WebSocket, 印尼语)<br>
            • AI: OpenAI GPT-3.5-turbo<br>
            • VAD: WebRTC实时检测
        </div>
        
        <div id="status" class="status-idle">等待拨号</div>
        
        <input type="text" id="phone" placeholder="输入电话号码 (例如: 85211111111)" value="">
        
        <button class="btn-call" onclick="makeCall()">📞 拨打电话</button>
        <button class="btn-hangup" onclick="hangup()" disabled>📴 挂断电话</button>
        
        <div class="info">
            <strong>使用说明:</strong><br>
            1. 输入目标电话号码<br>
            2. 点击"拨打电话"<br>
            3. 接通后与AI对话（印尼语）<br>
            4. 系统会自动识别、回复和录音
        </div>
    </div>
    
    <script>
        function updateStatus() {
            fetch('/status')
                .then(r => r.json())
                .then(data => {
                    const statusDiv = document.getElementById('status');
                    const callBtn = document.querySelector('.btn-call');
                    const hangupBtn = document.querySelector('.btn-hangup');
                    
                    statusDiv.className = '';
                    
                    if (data.status === 'idle') {
                        statusDiv.textContent = '等待拨号';
                        statusDiv.className = 'status-idle';
                        callBtn.disabled = false;
                        hangupBtn.disabled = true;
                    } else if (data.status === 'calling') {
                        statusDiv.textContent = '正在呼叫: ' + data.number;
                        statusDiv.className = 'status-calling';
                        callBtn.disabled = true;
                        hangupBtn.disabled = false;
                    } else if (data.status === 'connected') {
                        statusDiv.textContent = '通话中: ' + data.number + ' (AI对话已激活)';
                        statusDiv.className = 'status-connected';
                        callBtn.disabled = true;
                        hangupBtn.disabled = false;
                    }
                });
        }
        
        function makeCall() {
            const phone = document.getElementById('phone').value.trim();
            if (!phone) {
                alert('请输入电话号码');
                return;
            }
            
            fetch('/call', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({number: phone})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    updateStatus();
                } else {
                    alert('拨号失败: ' + data.error);
                }
            });
        }
        
        function hangup() {
            fetch('/hangup', {method: 'POST'})
                .then(r => r.json())
                .then(data => {
                    updateStatus();
                });
        }
        
        // 定期更新状态
        setInterval(updateStatus, 1000);
        updateStatus();
    </script>
</body>
</html>"""
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def handle_status(self):
        """获取系统状态"""
        global current_call
        
        status = {'status': 'idle', 'number': ''}
        
        with call_lock:
            if current_call and current_call.is_valid():
                try:
                    info = current_call.info()
                    if info.state == pj.CallState.CONFIRMED:
                        status['status'] = 'connected'
                    elif info.state in [pj.CallState.CALLING, pj.CallState.EARLY]:
                        status['status'] = 'calling'
                    status['number'] = info.remote_uri
                except:
                    pass
        
        self.send_json(status)
    
    def handle_call(self):
        """处理拨号请求"""
        global current_call
        
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            number = data.get('number', '').strip()
            if not number:
                self.send_json({'success': False, 'error': '电话号码为空'})
                return
            
            with call_lock:
                if current_call and current_call.is_valid():
                    self.send_json({'success': False, 'error': '已有通话进行中'})
                    return
                
                # 拨号
                full_number = f"{CONFIG['prefix']}{number}"
                uri = f"sip:{full_number}@{CONFIG['server']}"
                
                print(f"\n[拨号] {uri}")
                
                try:
                    acc = pj.Lib.instance().accounts[0]
                    call = acc.make_call(uri)
                    call.set_callback(AIConversationCallback(call))
                    current_call = call
                    
                    self.send_json({'success': True, 'uri': uri})
                except Exception as e:
                    self.send_json({'success': False, 'error': str(e)})
        
        except Exception as e:
            self.send_json({'success': False, 'error': str(e)})
    
    def handle_hangup(self):
        """处理挂断请求"""
        global current_call
        
        with call_lock:
            if current_call and current_call.is_valid():
                try:
                    current_call.hangup()
                    self.send_json({'success': True})
                except Exception as e:
                    self.send_json({'success': False, 'error': str(e)})
            else:
                self.send_json({'success': False, 'error': '无活动通话'})
    
    def send_json(self, data):
        """发送JSON响应"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())


# ==================== 主程序 ====================

def main():
    print("=" * 70)
    print("  AI对话系统 - 阿里云NLS WebSocket完整集成版")
    print("=" * 70)
    print(f"  ASR: 阿里云NLS实时识别")
    print(f"  TTS: 阿里云NLS语音合成 (发音人: {CONFIG['nls_tts_voice']})")
    print(f"  AI:  OpenAI {CONFIG['ai_model']}")
    print(f"  VAD: WebRTC (激进度: {CONFIG['vad_aggressiveness']})")
    print("=" * 70)
    
    # 检查配置
    if not CONFIG['openai_api_key']:
        print("\n⚠ 警告: 未设置 OPENAI_API_KEY 环境变量")
        print("  请运行: export OPENAI_API_KEY='your-key-here'")
        return
    
    # 初始化PJSUA
    lib = pj.Lib()
    
    try:
        # 创建配置
        ua_cfg = pj.UAConfig()
        ua_cfg.max_calls = 4
        
        media_cfg = pj.MediaConfig()
        media_cfg.clock_rate = 8000
        media_cfg.audio_frame_ptime = 20
        media_cfg.ec_tail_len = 0
        
        log_cfg = pj.LogConfig()
        log_cfg.level = CONFIG['log_level']
        
        # 初始化
        lib.init(ua_cfg, log_cfg, media_cfg)
        
        # 启动传输
        transport = lib.create_transport(pj.TransportType.UDP, pj.TransportConfig(CONFIG['port']))
        print(f"\n[SIP] 传输启动: UDP 端口 {CONFIG['port']}")
        
        # 启动库
        lib.start()
        
        # 创建账户
        acc_cfg = pj.AccountConfig()
        acc_cfg.id = f"sip:{CONFIG['caller_number']}@{CONFIG['server']}"
        acc_cfg.reg_uri = f"sip:{CONFIG['server']}"
        
        acc = lib.create_account(acc_cfg)
        acc.set_callback(MyAccountCallback(acc))
        
        print(f"[SIP] 账户创建: {acc_cfg.id}")
        
        # 启动HTTP服务器
        server = HTTPServer((CONFIG['api_host'], CONFIG['api_port']), APIHandler)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        
        print(f"\n[HTTP] Web界面: http://localhost:{CONFIG['api_port']}")
        print("\n✓ 系统已启动，可以通过Web界面拨打电话")
        print("  按 Ctrl+C 退出\n")
        
        # 主循环
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n[退出] 正在关闭系统...")
        
        # 清理
        lib.destroy()
        lib = None
        
        print("[退出] 系统已关闭\n")
    
    except pj.Error as e:
        print(f"\n[错误] PJSUA错误: {e}")
        if lib:
            lib.destroy()
    except Exception as e:
        print(f"\n[错误] 系统错误: {e}")
        import traceback
        traceback.print_exc()
        if lib:
            lib.destroy()


if __name__ == "__main__":
    main()


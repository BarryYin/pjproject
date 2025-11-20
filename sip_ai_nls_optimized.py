#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI对话系统 - 阿里云NLS WebSocket优化版
核心优化：
1. 预建立WebSocket连接
2. 复用recognizer和synthesizer
3. 长连接模式，不重复建立连接
"""

import sys
import time
import pjsua as pj
import threading
import os
import json
import wave
import webrtcvad
from datetime import datetime
import queue

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
    'recordings_dir': '/home/henry/pjproject/recordings',
    'temp_dir': '/home/henry/pjproject/temp_audio',
    
    # 阿里云NLS配置
    'nls_akid': 'LTAI5tGtuuJyivveR3UFARYs',
    'nls_akkey': 'aY32qhvLBpslrxwTUSO6tYlMscCitG',
    'nls_appkey': 'dqAnq24vXe5lJUlq',
    'nls_tts_voice': 'indah',  # 印尼语女声
    
    # OpenAI配置
    'openai_api_key': os.getenv('OPENAI_API_KEY', ''),
    'ai_model': 'gpt-3.5-turbo',
    
    # WebRTC VAD配置 - 优化版
    'vad_aggressiveness': 1,
    'vad_frame_duration': 30,
    'vad_silence_frames': 15,
    'vad_min_speech_frames': 3,
    'vad_max_speech_frames': 100,
}

for d in [CONFIG['temp_dir'], CONFIG['recordings_dir']]:
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
        self.max_speech_frames = CONFIG['vad_max_speech_frames']
    
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
                        print("  [VAD] 检测到说话...")
                    
                    self.speech_frames.append(frame)
                    self.silence_count = 0
                    
                    # 达到最大长度，强制结束
                    if len(self.speech_frames) >= self.max_speech_frames:
                        print(f"  [VAD] 达到最大长度 ({len(self.speech_frames)}帧)")
                        speech_audio = b''.join(self.speech_frames)
                        self.reset()
                        return ('speech_complete', speech_audio)
                else:
                    if self.is_speaking:
                        self.silence_count += 1
                        self.speech_frames.append(frame)
                        
                        if self.silence_count >= self.silence_threshold:
                            if len(self.speech_frames) >= self.min_speech_frames:
                                print(f"  [VAD] 句子结束 ({len(self.speech_frames)}帧)")
                                speech_audio = b''.join(self.speech_frames)
                                self.reset()
                                return ('speech_complete', speech_audio)
                            else:
                                self.reset()
                
            except Exception as e:
                pass
            
            offset += self.frame_size
        
        return None
    
    def reset(self):
        self.is_speaking = False
        self.speech_frames = []
        self.silence_count = 0


# ==================== 优化的NLS ASR引擎 ====================

class OptimizedNLSASREngine:
    """优化的阿里云NLS ASR引擎 - 保持连接"""
    
    def __init__(self):
        self.token = None
        self.appkey = CONFIG['nls_appkey']
        self.recognizer = None  # 保持recognizer
        self.lock = threading.Lock()
        self.last_request_time = 0  # 上次请求时间
        self.min_interval = 0.5  # 最小请求间隔（秒）
        
        # 预获取Token
        print("  [ASR] 预获取Token...")
        self.get_token()
        
        # 预创建recognizer
        print("  [ASR] 预创建recognizer...")
        self._create_recognizer()
    
    def get_token(self):
        """获取Token"""
        try:
            self.token = getToken(CONFIG['nls_akid'], CONFIG['nls_akkey'])
            print(f"  [ASR] Token: {self.token[:20]}...")
            return True
        except Exception as e:
            print(f"  [ASR] Token失败: {e}")
            return False
    
    def _create_recognizer(self):
        """创建recognizer（只创建一次）"""
        if self.recognizer:
            return
        
        try:
            self.recognizer = nls.NlsSpeechRecognizer(
                token=self.token,
                appkey=self.appkey,
                on_start=lambda msg, *args: print("  [ASR] ✓ 已启动"),
                on_completed=self._on_completed,
                on_error=lambda msg, *args: print(f"  [ASR] ✗ 错误: {msg}"),
                on_close=lambda *args: print("  [ASR] ⊗ 关闭")
            )
            print("  [ASR] Recognizer创建成功")
        except Exception as e:
            print(f"  [ASR] 创建失败: {e}")
            self.recognizer = None
    
    def _on_completed(self, message, *args):
        """完成回调"""
        try:
            msg = json.loads(message)
            if 'payload' in msg and 'result' in msg['payload']:
                self.result = msg['payload']['result']
                print(f"  [ASR] ✓ 完成")
            else:
                print(f"  [ASR] ⚠ 空结果")
                self.result = ""
        except Exception as e:
            print(f"  [ASR] 解析错误: {e}")
            self.result = ""
        
        self.completed = True
    
    def transcribe(self, audio_file):
        """快速识别 - 复用连接"""
        with self.lock:
            # 限流：确保请求间隔
            elapsed = time.time() - self.last_request_time
            if elapsed < self.min_interval:
                wait_time = self.min_interval - elapsed
                print(f"  [ASR] 限流等待{wait_time:.1f}s...", end=" ")
                time.sleep(wait_time)
            
            if not self.recognizer:
                self._create_recognizer()
            
            if not self.recognizer:
                return ""
            
            try:
                start_time = time.time()
                self.last_request_time = start_time
                
                # 读取音频
                with open(audio_file, 'rb') as f:
                    audio_data = f.read()
                
                print(f"  [ASR] 音频: {len(audio_data)}字节", end=" ")
                
                # 重置状态
                self.result = ""
                self.completed = False
                
                # 启动识别（复用WebSocket）
                # 注意：阿里云NLS自动语言检测，如果识别成中文说明音频有问题
                # 或者环境噪音被误识别了
                try:
                    self.recognizer.start(
                        aformat="pcm",
                        sample_rate=8000,
                        enable_intermediate_result=False
                    )
                except Exception as e:
                    print(f"start失败: {e}, 重建recognizer")
                    self.recognizer = None
                    self._create_recognizer()
                    if not self.recognizer:
                        return ""
                    self.recognizer.start(
                        aformat="pcm",
                        sample_rate=8000,
                        enable_intermediate_result=False
                    )
                
                # 快速发送音频
                chunk_size = 6400
                for i in range(0, len(audio_data), chunk_size):
                    self.recognizer.send_audio(audio_data[i:i+chunk_size])
                
                # 停止
                self.recognizer.stop()
                
                # 等待结果（短超时）
                timeout = 0
                while not self.completed and timeout < 50:  # 5秒
                    time.sleep(0.1)
                    timeout += 1
                
                elapsed = time.time() - start_time
                
                if self.result:
                    print(f"→ '{self.result}' ({elapsed:.1f}s)")
                else:
                    print(f"→ 超时 ({elapsed:.1f}s)")
                
                return self.result
                
            except Exception as e:
                print(f"  [ASR] 异常: {e}")
                # 重建recognizer
                self.recognizer = None
                self._create_recognizer()
                return ""


# ==================== 优化的NLS TTS引擎 ====================

class OptimizedNLSTTSEngine:
    """优化的阿里云NLS TTS引擎 - 保持连接"""
    
    def __init__(self):
        self.token = None
        self.appkey = CONFIG['nls_appkey']
        self.voice = CONFIG['nls_tts_voice']
        self.synthesizer = None
        self.lock = threading.Lock()
        self.last_request_time = 0  # 上次请求时间
        self.min_interval = 0.5  # 最小请求间隔（秒）
        
        # 预获取Token
        print("  [TTS] 预获取Token...")
        self.get_token()
        
        # 预创建synthesizer
        print("  [TTS] 预创建synthesizer...")
        self._create_synthesizer()
    
    def get_token(self):
        """获取Token"""
        try:
            self.token = getToken(CONFIG['nls_akid'], CONFIG['nls_akkey'])
            print(f"  [TTS] Token: {self.token[:20]}...")
            return True
        except Exception as e:
            print(f"  [TTS] Token失败: {e}")
            return False
    
    def _create_synthesizer(self):
        """创建synthesizer（只创建一次）"""
        if self.synthesizer:
            return
        
        try:
            self.synthesizer = nls.NlsSpeechSynthesizer(
                token=self.token,
                appkey=self.appkey,
                on_data=self._on_data,
                on_completed=lambda msg, *args: self._on_completed(),
                on_error=lambda msg, *args: print(f"  [TTS] ✗ 错误: {msg}"),
                on_close=lambda *args: print("  [TTS] ⊗ 关闭")
            )
            print("  [TTS] Synthesizer创建成功")
        except Exception as e:
            print(f"  [TTS] 创建失败: {e}")
            self.synthesizer = None
    
    def _on_data(self, data, *args):
        """数据回调"""
        if self.audio_file:
            self.audio_file.write(data)
    
    def _on_completed(self):
        """完成回调"""
        if self.audio_file:
            try:
                self.audio_file.flush()  # 确保数据写入
                self.audio_file.close()
                self.audio_file = None
                print("  [TTS] ✓ 完成（文件已关闭）")
            except Exception as e:
                print(f"  [TTS] ⚠ 关闭文件错误: {e}")
        else:
            print("  [TTS] ✓ 完成（无文件）")
        self.completed = True
    
    def synthesize(self, text):
        """快速合成 - 复用连接"""
        with self.lock:
            # 限流：确保请求间隔
            elapsed = time.time() - self.last_request_time
            if elapsed < self.min_interval:
                wait_time = self.min_interval - elapsed
                print(f"  [TTS] 限流等待{wait_time:.1f}s...", end=" ")
                time.sleep(wait_time)
            
            if not text or not text.strip():
                return None
            
            if not self.synthesizer:
                self._create_synthesizer()
            
            if not self.synthesizer:
                return None
            
            try:
                start_time = time.time()
                self.last_request_time = start_time
                
                # 输出文件
                ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                output_file = os.path.join(CONFIG['temp_dir'], f"tts_{ts}.wav")
                
                print(f"  [TTS] 文本: '{text[:30]}...'", end=" ")
                
                # 重置状态
                self.audio_file = open(output_file, 'wb')
                self.completed = False
                
                # 开始合成（复用WebSocket）
                self.synthesizer.start(
                    text=text,
                    voice=self.voice,
                    aformat="wav",
                    sample_rate=8000,
                    volume=50,
                    speech_rate=0
                )
                
                # 等待完成（短超时）
                timeout = 0
                while not self.completed and timeout < 100:  # 10秒
                    time.sleep(0.1)
                    timeout += 1
                
                elapsed = time.time() - start_time
                
                # 检查文件
                if os.path.exists(output_file):
                    size = os.path.getsize(output_file)
                    if size > 0:
                        print(f"→ {size}字节 ({elapsed:.1f}s)")
                        return output_file
                    else:
                        print(f"→ 文件为空 ({elapsed:.1f}s)")
                        return None
                else:
                    print(f"→ 文件不存在 ({elapsed:.1f}s)")
                    return None
                    
            except Exception as e:
                print(f"  [TTS] 异常: {e}")
                # 重建synthesizer
                if self.audio_file:
                    self.audio_file.close()
                self.synthesizer = None
                self._create_synthesizer()
                return None


# ==================== AI对话引擎 ====================

class DialogueEngine:
    """AI对话引擎"""
    
    def __init__(self):
        self.conversation_history = []
        self.system_prompt = """You are a helpful AI assistant speaking in Indonesian.
Keep responses concise and natural (1-2 sentences).
You are having a phone conversation, so be conversational and friendly."""
    
    def get_response(self, user_input):
        """获取AI回复"""
        if not CONFIG['openai_api_key']:
            return "Maaf, saya tidak dapat menjawab."
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=CONFIG['openai_api_key'])
            
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(self.conversation_history[-6:])
            messages.append({"role": "user", "content": user_input})
            
            response = client.chat.completions.create(
                model=CONFIG['ai_model'],
                messages=messages,
                max_tokens=150,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            self.conversation_history.append({"role": "user", "content": user_input})
            self.conversation_history.append({"role": "assistant", "content": ai_response})
            
            return ai_response
            
        except Exception as e:
            print(f"  [AI] 错误: {e}")
            return "Maaf, terjadi kesalahan."


# ==================== 实时录音读取器 ====================

class RealtimeWavReader:
    """实时读取录音文件"""
    
    def __init__(self, filename):
        self.filename = filename
        self.last_pos = 0
    
    def read_new_data(self):
        """读取新增数据"""
        try:
            file_size = os.path.getsize(self.filename)
            if file_size > self.last_pos:
                with open(self.filename, 'rb') as f:
                    f.seek(self.last_pos)
                    new_data = f.read(file_size - self.last_pos)
                    self.last_pos = file_size
                    return new_data
        except:
            pass
        return b''


# ==================== AI对话回调 ====================

class AIConversationCallback(pj.CallCallback):
    """AI对话回调"""
    
    def __init__(self, call=None):
        pj.CallCallback.__init__(self, call)
        self.connected = False
        self.lock = threading.Lock()
        
        self.vad = WebRTCVADDetector(CONFIG['vad_aggressiveness'], CONFIG['vad_frame_duration'])
        self.wav_reader = None
        self.vad_thread = None
        self.vad_running = False
        
        # 使用优化版引擎
        self.asr = OptimizedNLSASREngine()
        self.tts = OptimizedNLSTTSEngine()
        self.dialogue = DialogueEngine()
        
        self.recorder = None
        self.recorder_id = None
        self.record_file = None
        
        # 播放队列（避免线程问题）
        self.play_queue = queue.Queue()
        self.play_thread = None
        self.play_running = False
        self.current_player = None  # 当前播放器
        self.current_player_slot = None
    
    def on_state(self):
        """状态变化"""
        try:
            info = self.call.info()
            print(f"\n[状态] {info.state_text}")
            
            if info.state == pj.CallState.CONFIRMED:
                with self.lock:
                    self.connected = True
                print("[状态] >>> 通话已接通\n")
                self.start_vad_recording()
                
            elif info.state == pj.CallState.DISCONNECTED:
                with self.lock:
                    self.connected = False
                print("\n[状态] >>> 通话已结束")
                # 立即清理播放器，避免通话结束后还在操作
                self.stop_current_playback()
                # 停止录音和线程
                self.stop_vad_recording()
        except:
            pass
    
    def on_media_state(self):
        """媒体状态"""
        try:
            info = self.call.info()
            if info.media_state == pj.MediaState.ACTIVE:
                call_slot = info.conf_slot
                pj.Lib.instance().conf_connect(call_slot, 0)
                pj.Lib.instance().conf_connect(0, call_slot)
        except:
            pass
    
    def start_vad_recording(self):
        """开始录音"""
        try:
            info = self.call.info()
            
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.record_file = os.path.join(CONFIG['recordings_dir'], f"call_{ts}.wav")
            
            self.recorder = pj.Lib.instance().create_recorder(self.record_file)
            self.recorder_id = pj.Lib.instance().recorder_get_slot(self.recorder)
            
            call_slot = info.conf_slot
            pj.Lib.instance().conf_connect(call_slot, self.recorder_id)
            
            print(f"[录音] {self.record_file}")
            
            self.wav_reader = RealtimeWavReader(self.record_file)
            
            # 启动VAD线程
            self.vad_running = True
            self.vad_thread = threading.Thread(target=self.vad_process_loop, daemon=True)
            self.vad_thread.start()
            
            # 启动播放线程
            self.play_running = True
            self.play_thread = threading.Thread(target=self.play_loop, daemon=True)
            self.play_thread.start()
            
        except Exception as e:
            print(f"[错误] {e}")
    
    def stop_vad_recording(self):
        """停止录音"""
        try:
            # 停止VAD线程
            self.vad_running = False
            if self.vad_thread:
                self.vad_thread.join(timeout=2)
            
            # 停止播放线程
            self.play_running = False
            if self.play_thread:
                self.play_thread.join(timeout=2)
            
            if self.recorder_id is not None:
                try:
                    pj.Lib.instance().conf_disconnect(self.call.info().conf_slot, self.recorder_id)
                except:
                    pass
            
            if self.recorder:
                try:
                    pj.Lib.instance().recorder_destroy(self.recorder)
                except:
                    pass
            
            print(f"[录音] 已保存")
        except:
            pass
    
    def vad_process_loop(self):
        """VAD处理循环"""
        try:
            # 注册线程到PJSIP
            pj.Lib.instance().thread_register("VAD线程")
            print("[VAD] VAD线程已启动")
            
            last_read_time = time.time()
            read_interval = 0.1
            
            while self.vad_running:
                try:
                    # 检查通话状态
                    if not self.connected:
                        time.sleep(0.5)
                        continue
                    
                    current_time = time.time()
                    
                    if current_time - last_read_time >= read_interval:
                        new_data = self.wav_reader.read_new_data()
                        last_read_time = current_time
                        
                        if new_data and self.wav_reader.last_pos > 44:
                            result = self.vad.process_audio(new_data)
                            
                            # 检测到说话：打断当前播放
                            if self.vad.is_speaking and self.current_player and self.connected:
                                print("  [打断] 检测到说话，停止播放")
                                self.stop_current_playback()
                            
                            if result and result[0] == 'speech_complete' and self.connected:
                                self.process_speech(result[1])
                    
                    time.sleep(0.05)
                except:
                    time.sleep(0.5)
        except Exception as e:
            print(f"[VAD] 线程错误: {e}")
    
    def process_speech(self, audio_data):
        """处理语音 - 独立线程"""
        thread = threading.Thread(target=self._process_speech_thread, args=(audio_data,), daemon=True)
        thread.start()
    
    def _process_speech_thread(self, audio_data):
        """处理语音线程"""
        try:
            # 首先检查通话是否还有效
            if not self.connected:
                print("  [处理] 通话已结束，跳过处理")
                return
            
            print("\n" + "━" * 50)
            
            # 保存音频
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            speech_file = os.path.join(CONFIG['temp_dir'], f"speech_{ts}.wav")
            
            with wave.open(speech_file, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(8000)
                wf.writeframes(audio_data)
            
            # 再次检查通话状态（ASR可能耗时）
            if not self.connected:
                print("  [处理] 通话已结束，跳过ASR")
                return
            
            # ASR识别（复用连接，快！）
            text = self.asr.transcribe(speech_file)
            
            if text and self.connected:
                # AI回复
                print(f"  [AI] 用户: '{text}'")
                response = self.dialogue.get_response(text)
                print(f"  [AI] 回复: '{response}'")
                
                if response and self.connected:
                    # TTS合成（复用连接，快！）
                    tts_file = self.tts.synthesize(response)
                    print(f"  [TTS] 返回文件: {tts_file}")
                    
                    if tts_file and self.connected:
                        print(f"  [TTS] 准备播放: {tts_file}")
                        # 加入播放队列，避免线程问题
                        self.play_queue.put(tts_file)
                    else:
                        print(f"  [TTS] ✗ 文件为空或通话已结束")
            
            print("━" * 50 + "\n")
        except Exception as e:
            print(f"[错误] {e}")
    
    def play_loop(self):
        """播放循环 - 在独立线程中运行，注册到PJSIP"""
        try:
            # 注册线程到PJSIP
            pj.Lib.instance().thread_register("播放线程")
            print("[播放] 播放线程已启动")
            
            while self.play_running:
                try:
                    # 从队列获取文件（非阻塞，1秒超时）
                    audio_file = self.play_queue.get(timeout=1)
                    
                    # 检查通话是否还在
                    if not self.connected:
                        print("  [播放] 通话已结束，跳过播放")
                        continue
                    
                    self._play_audio(audio_file)
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"  [播放] 错误: {e}")
        except Exception as e:
            print(f"[播放] 线程错误: {e}")
    
    def stop_current_playback(self):
        """停止当前播放"""
        try:
            if self.current_player and self.current_player_slot:
                # 检查通话是否还有效
                if self.call.is_valid() and self.connected:
                    try:
                        pj.Lib.instance().conf_disconnect(self.current_player_slot, self.call.info().conf_slot)
                    except:
                        pass  # 如果断开失败，忽略
                
                # 销毁播放器
                try:
                    pj.Lib.instance().player_destroy(self.current_player)
                except:
                    pass
                
                self.current_player = None
                self.current_player_slot = None
        except:
            pass
    
    def _play_audio(self, audio_file):
        """实际播放音频"""
        try:
            print("  [播放] 正在播放...", end=" ")
            
            # 检查通话状态
            if not self.call.is_valid() or not self.connected:
                print("通话已结束")
                return
            
            # 创建播放器
            player = pj.Lib.instance().create_player(audio_file, loop=False)
            player_slot = pj.Lib.instance().player_get_slot(player)
            
            # 保存当前播放器
            self.current_player = player
            self.current_player_slot = player_slot
            
            # 连接到通话
            info = self.call.info()
            pj.Lib.instance().conf_connect(player_slot, info.conf_slot)
            
            # 估算播放时间（根据文件大小）
            try:
                import os
                file_size = os.path.getsize(audio_file)
                # 8000Hz 单声道 16-bit = 16000 bytes/sec
                duration = file_size / 16000.0
                print(f"预计{duration:.1f}秒...", end=" ")
                
                # 分段等待，每0.1秒检查一次是否被打断
                elapsed = 0
                while elapsed < duration + 0.5:
                    time.sleep(0.1)
                    elapsed += 0.1
                    
                    # 如果被打断或播放器被清空，提前退出
                    if not self.current_player:
                        print("被打断")
                        return
            except:
                # 默认等待3秒
                time.sleep(3)
            
            # 清理
            try:
                # 检查通话是否还有效
                if self.call.is_valid() and self.connected:
                    pj.Lib.instance().conf_disconnect(player_slot, info.conf_slot)
                pj.Lib.instance().player_destroy(player)
                self.current_player = None
                self.current_player_slot = None
            except:
                pass
            
            print("完成")
        except Exception as e:
            print(f"失败: {e}")
            # 清理失败也要重置标记
            self.current_player = None
            self.current_player_slot = None


# ==================== 主程序 ====================

def main():
    if len(sys.argv) < 2:
        print("使用: python3 sip_ai_nls_optimized.py <电话号码>")
        return
    
    phone_number = sys.argv[1].strip()
    
    print("=" * 70)
    print("  AI对话系统 - NLS优化版（长连接）")
    print("=" * 70)
    print(f"  特性: WebSocket长连接复用，极速ASR/TTS")
    print("=" * 70)
    
    if not CONFIG['openai_api_key']:
        print("\n⚠ 错误: 未设置 OPENAI_API_KEY")
        return
    
    lib = pj.Lib()
    
    try:
        ua_cfg = pj.UAConfig()
        ua_cfg.max_calls = 4
        
        media_cfg = pj.MediaConfig()
        media_cfg.clock_rate = 8000
        media_cfg.audio_frame_ptime = 20
        media_cfg.ec_tail_len = 0
        
        log_cfg = pj.LogConfig()
        log_cfg.level = CONFIG['log_level']
        
        lib.init(ua_cfg, log_cfg, media_cfg)
        transport = lib.create_transport(pj.TransportType.UDP, pj.TransportConfig(CONFIG['port']))
        lib.start()
        
        acc_cfg = pj.AccountConfig()
        acc_cfg.id = f"sip:{CONFIG['caller_number']}@{CONFIG['server']}"
        acc_cfg.reg_uri = f"sip:{CONFIG['server']}"
        acc = lib.create_account(acc_cfg)
        
        print(f"\n[SIP] 账户: {CONFIG['caller_number']}")
        
        # 拨号
        full_number = f"{CONFIG['prefix']}{phone_number}"
        uri = f"sip:{full_number}@{CONFIG['server']}"
        
        print(f"[拨号] {uri}")
        print("[提示] 按 Ctrl+C 挂断\n")
        
        call = acc.make_call(uri)
        call.set_callback(AIConversationCallback(call))
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n[挂断]...")
            if call.is_valid():
                call.hangup()
            time.sleep(2)
        
        lib.destroy()
        print("[退出]\n")
    
    except Exception as e:
        print(f"\n[错误] {e}")
        if lib:
            lib.destroy()


if __name__ == "__main__":
    main()

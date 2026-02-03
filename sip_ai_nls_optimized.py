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
    
    # 阿里云NLS配置 - 使用环境变量
    'nls_akid': os.getenv('ALI_NLS_AKID', ''),
    'nls_akkey': os.getenv('ALI_NLS_AKKEY', ''),
    'nls_appkey': os.getenv('ALI_NLS_APPKEY', ''),
    'nls_tts_voice': 'indah',  # 印尼语女声
    
    # OpenAI配置
    'openai_api_key': os.getenv('OPENAI_API_KEY', ''),
    'ai_model': 'gpt-3.5-turbo',
    
    # WebRTC VAD配置 - 优化版
    'vad_aggressiveness': 1,
    'vad_frame_duration': 30,
    'vad_silence_frames': 15,
    'vad_min_speech_frames': 10,             # 增加到10帧（300ms）- 过滤更短的语音
    'vad_max_speech_frames': 100,
    
    # 智能打断配置
    'smart_interrupt_enabled': False,         # 暂时禁用智能打断（减少ASR调用）
    'interrupt_min_frames': 15,               # 打断最少帧数（450ms）
    'interrupt_check_semantic': False,        # 禁用LLM语义检查
    'interrupt_semantic_threshold': 0.3,      # 语义相关度阈值
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
        self.min_interval = 3.0  # 最小请求间隔（秒）- 增加到3秒避免限流
        self.error_count = 0  # 错误计数
        self.max_errors = 3  # 最大错误次数，超过则重建连接
        self.last_rate_limit_time = 0  # 上次限流时间
        self.rate_limit_backoff = 10.0  # 限流后的退避时间（秒）- 增加到10秒
        
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
    
    def _on_error(self, message, *args):
        """错误回调 - 检测限流错误"""
        print(f"  [ASR] ✗ 错误: {message}")
        # 检查是否是限流错误
        if message and "TOO_MANY_REQUESTS" in str(message):
            print(f"  [ASR] ⚠ 触发限流，启动退避")
            self.last_rate_limit_time = time.time()
    
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
                on_error=self._on_error,
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
    
    def transcribe(self, audio_file, is_interrupt_check=False):
        """快速识别 - 复用连接
        
        Args:
            audio_file: 音频文件路径
            is_interrupt_check: 是否是打断检查（如果是，使用更长的限流）
        """
        with self.lock:
            # 检查是否刚触发过限流，如果是则延长等待时间
            time_since_rate_limit = time.time() - self.last_rate_limit_time
            if time_since_rate_limit < self.rate_limit_backoff:
                backoff_wait = self.rate_limit_backoff - time_since_rate_limit
                print(f"  [ASR] 限流退避等待{backoff_wait:.1f}s...", end=" ")
                time.sleep(backoff_wait)
            
            # 限流：确保请求间隔
            # 打断检查使用更长的间隔，避免过于频繁
            min_interval = self.min_interval * 2 if is_interrupt_check else self.min_interval
            elapsed = time.time() - self.last_request_time
            if elapsed < min_interval:
                wait_time = min_interval - elapsed
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
                    print(f"start失败: {e}, 重建")
                    self.recognizer = None
                    self._create_recognizer()
                    if not self.recognizer:
                        self.error_count += 1
                        return ""
                    
                    # 重试start
                    try:
                        self.recognizer.start(
                            aformat="pcm",
                            sample_rate=8000,
                            enable_intermediate_result=False
                        )
                    except Exception as e2:
                        print(f"重试start失败: {e2}")
                        self.error_count += 1
                        return ""
                
                # 快速发送音频
                try:
                    chunk_size = 6400
                    for i in range(0, len(audio_data), chunk_size):
                        self.recognizer.send_audio(audio_data[i:i+chunk_size])
                    
                    # 停止
                    self.recognizer.stop()
                except Exception as e:
                    print(f"send/stop失败: {e}")
                    self.error_count += 1
                    # 不立即重建，等待下次检查error_count
                    return ""
                
                # 等待结果（短超时）
                timeout = 0
                while not self.completed and timeout < 50:  # 5秒
                    time.sleep(0.1)
                    timeout += 1
                
                elapsed = time.time() - start_time
                
                if self.result:
                    print(f"→ '{self.result}' ({elapsed:.1f}s)")
                    self.error_count = 0  # 成功，重置错误计数
                else:
                    print(f"→ 超时 ({elapsed:.1f}s)")
                    self.error_count += 1
                
                return self.result
                
            except Exception as e:
                print(f"  [ASR] 异常: {e}")
                self.error_count += 1
                
                # 只在错误次数过多时才重建recognizer
                if self.error_count >= self.max_errors:
                    print(f"  [ASR] 错误过多({self.error_count}次)，强制重建连接")
                    self.recognizer = None
                    self._create_recognizer()
                    self.error_count = 0
                
                # 否则保持连接，不重建
                return ""


# ==================== DashScope TTS引擎 ====================

class DashScopeTTSEngine:
    """阿里云DashScope TTS引擎 - 使用HTTP API"""
    
    def __init__(self):
        import dashscope
        from dashscope.audio.tts import SpeechSynthesizer
        
        self.dashscope = dashscope
        self.SpeechSynthesizer = SpeechSynthesizer
        self.lock = threading.Lock()
        self.last_request_time = 0  # 上次请求时间
        self.min_interval = 1.0  # 最小请求间隔（秒）- DashScope限流较宽松
        self.error_count = 0  # 错误计数
        self.max_errors = 3  # 最大错误次数
        
        # 设置API Key
        self.api_key = "sk-b20dbc29a6ab4ada8b4711d8b817f7cb"
        self.dashscope.api_key = self.api_key
        
        # TTS配置
        self.model = 'sambert-indah-v1'  # 印尼语女声
        self.sample_rate = 8000  # PJSIP使用8000Hz
        self.format = 'wav'
        
        print(f"  [TTS] DashScope引擎初始化完成")
    
    def synthesize(self, text):
        """使用DashScope合成语音"""
        with self.lock:
            # 限流：确保请求间隔
            elapsed = time.time() - self.last_request_time
            if elapsed < self.min_interval:
                wait_time = self.min_interval - elapsed
                print(f"  [TTS] 限流等待{wait_time:.1f}s...", end=" ")
                time.sleep(wait_time)
            
            if not text or not text.strip():
                return None
            
            try:
                start_time = time.time()
                self.last_request_time = start_time
                
                # 输出文件
                ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                output_file = os.path.join(CONFIG['temp_dir'], f"tts_{ts}.wav")
                
                print(f"  [TTS] 文本: '{text[:30]}...'", end=" ")
                
                # 调用DashScope API
                result = self.SpeechSynthesizer.call(
                    model=self.model,
                    text=text,
                    sample_rate=self.sample_rate,
                    format=self.format
                )
                
                elapsed = time.time() - start_time
                
                # 检查结果
                if result.get_audio_data() is not None:
                    # 写入文件
                    with open(output_file, 'wb') as f:
                        f.write(result.get_audio_data())
                    
                    size = os.path.getsize(output_file)
                    print(f"→ {size}字节 ({elapsed:.1f}s)")
                    self.error_count = 0  # 成功，重置错误计数
                    return output_file
                else:
                    print(f"→ 无音频数据 ({elapsed:.1f}s)")
                    self.error_count += 1
                    return None
                    
            except Exception as e:
                elapsed = time.time() - start_time
                print(f"  [TTS] 异常: {e} ({elapsed:.1f}s)")
                self.error_count += 1
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

class SmartInterruptChecker:
    """智能打断检查器 - 使用LLM判断是否应该打断"""
    
    def __init__(self):
        self.interrupt_keywords = {
            # 印尼语常见无意义词
            'filler': ['eh', 'em', 'um', 'uh', 'ah', 'hmm', 'hm', 'mm'],
            # 印尼语简短回应
            'short_response': ['ya', 'iya', 'oh', 'ok', 'oke', 'baik', 'tidak', 'nggak'],
        }
    
    def should_interrupt(self, text, is_playing=False):
        """
        判断是否应该打断当前播放
        
        策略：
        1. 长度检查 - 太短直接忽略
        2. 关键词检查 - 无意义词/简短回应不打断
        3. LLM语义检查 - 判断是否有真实打断意图
        
        返回: (should_interrupt: bool, reason: str)
        """
        if not text or not text.strip():
            return False, "空文本"
        
        text_lower = text.lower().strip()
        
        # 策略1：长度检查（少于3个字符，可能是"嗯"、"哦"等）
        if len(text_lower) <= 2:
            return False, f"太短({len(text_lower)}字符)"
        
        # 策略2：关键词过滤
        # 检查是否是填充词
        for filler in self.interrupt_keywords['filler']:
            if text_lower == filler or text_lower.startswith(filler + ' '):
                return False, f"填充词({text_lower})"
        
        # 检查是否是单独的简短回应
        words = text_lower.split()
        if len(words) == 1 and words[0] in self.interrupt_keywords['short_response']:
            return False, f"简短回应({words[0]})"
        
        # 如果不在播放中，不需要打断判断
        if not is_playing:
            return True, "非播放中"
        
        # 策略3：LLM语义检查（可选）
        if CONFIG['interrupt_check_semantic']:
            return self._check_semantic_interrupt(text)
        
        # 默认：允许打断
        return True, "通过基本检查"
    
    def _check_semantic_interrupt(self, text):
        """使用LLM进行语义检查"""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=CONFIG['openai_api_key'])
            
            # 快速判断：是否是有意义的打断
            prompt = f"""Analyze if this user input should interrupt the current AI speech.

User said: "{text}"

Reply ONLY with one word:
- "YES" if: user asks a NEW question, makes a NEW statement, or clearly wants to interrupt
- "NO" if: just acknowledgment (eh, um, ya, oke), background noise, or simple response

Answer:"""
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=5,
                temperature=0
            )
            
            answer = response.choices[0].message.content.strip().upper()
            
            if answer.startswith('YES'):
                return True, "LLM判断:有打断意图"
            elif answer.startswith('NO'):
                return False, f"LLM判断:无打断意图({text})"
            else:
                # LLM返回不明确，保守起见允许打断
                return True, f"LLM不确定({answer})"
        
        except Exception as e:
            # LLM调用失败，回退到允许打断
            print(f"  [打断检查] LLM失败: {e}")
            return True, "LLM失败，允许打断"


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
        
        # 使用混合引擎：NLS ASR + DashScope TTS
        self.asr = OptimizedNLSASREngine()
        self.tts = DashScopeTTSEngine()
        self.dialogue = DialogueEngine()
        
        # 智能打断检查器
        self.interrupt_checker = SmartInterruptChecker()
        
        self.recorder = None
        self.recorder_id = None
        self.record_file = None
        
        # 播放队列（避免线程问题）
        self.play_queue = queue.Queue()
        self.play_thread = None
        self.play_running = False
        self.current_player = None  # 当前播放器
        self.current_player_slot = None
        
        # 打断缓冲区 - 存储检测到说话时的音频，用于快速ASR判断
        self.interrupt_buffer = []
        self.interrupt_buffer_lock = threading.Lock()
    
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
                print("\n[状态] >>> 通话已结束")
                # 先停止所有线程和清理资源（此时connected还是True）
                self.stop_vad_recording()
                # 最后设置connected为False
                with self.lock:
                    self.connected = False
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
            # 先清理当前播放
            self.stop_current_playback()
            
            # 停止VAD线程
            self.vad_running = False
            if self.vad_thread:
                self.vad_thread.join(timeout=2)
            
            # 停止播放线程
            self.play_running = False
            if self.play_thread:
                self.play_thread.join(timeout=2)
            
            # 断开录音器连接（安全检查）
            if self.recorder_id is not None:
                try:
                    # 检查通话是否还有效
                    if self.call.is_valid():
                        call_info = self.call.info()
                        # 检查conf_slot是否有效（>= 0）
                        if call_info.conf_slot >= 0 and self.recorder_id >= 0:
                            pj.Lib.instance().conf_disconnect(call_info.conf_slot, self.recorder_id)
                except Exception as e:
                    # 忽略断开连接的错误
                    pass
            
            # 销毁录音器
            if self.recorder:
                try:
                    pj.Lib.instance().recorder_destroy(self.recorder)
                except:
                    pass
                self.recorder = None
                self.recorder_id = None
            
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
                            
                            # 智能打断逻辑
                            if CONFIG['smart_interrupt_enabled']:
                                # 检测到说话开始
                                if self.vad.is_speaking:
                                    # 累积音频帧
                                    with self.interrupt_buffer_lock:
                                        self.interrupt_buffer.extend(self.vad.speech_frames[-5:])  # 最后5帧
                                    
                                    # 如果正在播放 且 累积足够长度，进行打断检查
                                    if self.current_player and self.connected:
                                        frame_count = len(self.vad.speech_frames)
                                        
                                        # 达到最小帧数才检查打断
                                        if frame_count >= CONFIG['interrupt_min_frames']:
                                            # 只检查一次（避免重复）
                                            if not hasattr(self, '_interrupt_checked'):
                                                self._interrupt_checked = True
                                                self.check_smart_interrupt()
                            else:
                                # 传统打断：立即打断
                                if self.vad.is_speaking and self.current_player and self.connected:
                                    print("  [打断] 检测到说话，停止播放")
                                    self.stop_current_playback()
                            
                            # 语音结束，处理完整句子
                            if result and result[0] == 'speech_complete' and self.connected:
                                # 重置打断检查标志
                                if hasattr(self, '_interrupt_checked'):
                                    delattr(self, '_interrupt_checked')
                                # 清空打断缓冲区
                                with self.interrupt_buffer_lock:
                                    self.interrupt_buffer = []
                                # 处理语音
                                self.process_speech(result[1])
                    
                    time.sleep(0.05)
                except:
                    time.sleep(0.5)
        except Exception as e:
            print(f"[VAD] 线程错误: {e}")
    
    def check_smart_interrupt(self):
        """智能打断检查 - 在独立线程中运行"""
        thread = threading.Thread(target=self._check_smart_interrupt_thread, daemon=True)
        thread.start()
    
    def _check_smart_interrupt_thread(self):
        """智能打断检查线程"""
        try:
            # 检查是否还在播放
            if not self.current_player:
                print("  [打断检查] 播放已结束，跳过")
                return
            
            # 获取当前缓冲区的音频
            with self.interrupt_buffer_lock:
                if not self.interrupt_buffer:
                    print("  [打断检查] 缓冲区为空")
                    return
                audio_data = b''.join(self.interrupt_buffer[-15:])  # 最后450ms音频
            
            # 检查音频长度是否足够
            if len(audio_data) < 8000:  # 少于0.5秒，太短
                print("  [打断检查] 音频太短，跳过")
                return
            
            # 快速ASR识别（标记为打断检查，使用更长的限流）
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            temp_file = os.path.join(CONFIG['temp_dir'], f"interrupt_{ts}.wav")
            
            with wave.open(temp_file, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(8000)
                wf.writeframes(audio_data)
            
            print("  [打断检查] ASR中...", end=" ")
            text = self.asr.transcribe(temp_file, is_interrupt_check=True)
            
            if not text:
                print("无文本")
                return
            
            print(f"'{text}'", end=" ")
            
            # 再次检查是否还在播放
            if not self.current_player:
                print("→ 播放已结束")
                return
            
            # 使用智能检查器判断
            should_interrupt, reason = self.interrupt_checker.should_interrupt(
                text, 
                is_playing=(self.current_player is not None)
            )
            
            if should_interrupt:
                print(f"→ 打断! ({reason})")
                self.stop_current_playback()
            else:
                print(f"→ 忽略 ({reason})")
                # 不打断，继续播放
        
        except Exception as e:
            print(f"  [打断检查] 错误: {e}")
    
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
    print("  AI对话系统 - 混合引擎版")
    print("=" * 70)
    print(f"  ASR引擎: 阿里云NLS (WebSocket)")
    print(f"  TTS引擎: 阿里云DashScope (HTTP)")
    print(f"  回声消除: 已启用 (400ms尾长)")
    
    if CONFIG['smart_interrupt_enabled']:
        semantic_status = "启用" if CONFIG['interrupt_check_semantic'] else "禁用"
        print(f"  智能打断: 已启用 (最少{CONFIG['interrupt_min_frames']}帧, LLM语义:{semantic_status})")
    else:
        print(f"  智能打断: 禁用（传统模式）")
    
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
        
        # 回声消除配置
        # ec_tail_len: 回声尾长（毫秒），建议200-800ms
        # 0 = 禁用回声消除
        # 200 = 适用于近距离对话
        # 400 = 标准配置，适用于大多数情况
        # 800 = 适用于长回声延迟的环境
        media_cfg.ec_tail_len = 400
        
        # ec_options: 回声消除选项
        # 0 = 默认（使用Speex AEC）
        # 1 = 使用WebRTC AEC（更好的效果，但需要编译时启用）
        media_cfg.ec_options = 0
        
        # 禁用VAF（Voice Activity Filter），因为我们用WebRTC VAD
        media_cfg.no_vad = True
        
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

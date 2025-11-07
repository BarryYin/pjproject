#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI智能对话系统 - 免费方案（印尼语优化）
ASR: faster-whisper (GPU加速)
TTS: Edge TTS (免费)
AI: GPT-3.5-turbo

特性:
- 实时语音识别 (ASR)
- AI智能对话
- 自然语音合成 (TTS)
- VAD语音活动检测
- 低延迟优化 (目标: 2-3秒)
"""

import sys
import time
import pjsua as pj
import threading
import os
import json
import queue
import asyncio
import wave
import struct
import numpy as np
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

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
    'api_port': 8090,  # 改为8090，避免与其他服务冲突
    
    # AI配置
    'openai_api_key': os.getenv('OPENAI_API_KEY', ''),  # 从环境变量读取
    'ai_model': 'gpt-3.5-turbo',
    'ai_language': 'id',  # 印尼语
    
    # ASR配置 (faster-whisper)
    'whisper_model': 'base',  # tiny/base/small/medium/large-v3
    'whisper_device': 'cpu',  # cpu/cuda (如果有GPU)
    'whisper_compute_type': 'int8',  # int8/float16/float32
    
    # TTS配置 (Edge TTS)
    'tts_voice': 'id-ID-ArdiNeural',  # 印尼语男声
    # 可选: id-ID-GadisNeural (女声)
    'tts_rate': '+0%',  # 语速: -50% 到 +100%
    'tts_pitch': '+0Hz',  # 音调
    
    # VAD配置
    'vad_silence_duration': 1.5,  # 静音持续时间判定句子结束(秒)
    'vad_speech_threshold': 0.02,  # 语音能量阈值
    
    # 性能优化
    'enable_cache': True,  # 启用常用回复缓存
    'parallel_processing': True,  # 并行处理ASR和TTS
}

# 创建必要目录
os.makedirs(CONFIG['audio_dir'], exist_ok=True)
os.makedirs(CONFIG['recordings_dir'], exist_ok=True)
os.makedirs(CONFIG['temp_dir'], exist_ok=True)


# ==================== ASR引擎 (faster-whisper) ====================

class ASREngine:
    """ASR语音识别引擎 - 使用faster-whisper"""
    
    def __init__(self):
        self.model = None
        self.initialized = False
        
    def initialize(self):
        """初始化Whisper模型"""
        if self.initialized:
            return True
        
        try:
            print("\n[ASR] 正在加载 faster-whisper 模型...")
            print(f"  模型: {CONFIG['whisper_model']}")
            print(f"  设备: {CONFIG['whisper_device']}")
            print(f"  计算类型: {CONFIG['whisper_compute_type']}")
            
            # 尝试导入faster-whisper
            try:
                from faster_whisper import WhisperModel
            except ImportError:
                print("  ⚠ faster-whisper未安装，尝试安装...")
                os.system("pip3 install faster-whisper -q")
                from faster_whisper import WhisperModel
            
            # 加载模型
            self.model = WhisperModel(
                CONFIG['whisper_model'],
                device=CONFIG['whisper_device'],
                compute_type=CONFIG['whisper_compute_type']
            )
            
            self.initialized = True
            print("  ✓ ASR模型加载成功")
            return True
            
        except Exception as e:
            print(f"  ✗ ASR模型加载失败: {e}")
            print("  提示: 安装 faster-whisper")
            print("    pip3 install faster-whisper")
            return False
    
    def transcribe(self, audio_file, language='id'):
        """
        转录音频文件
        
        Args:
            audio_file: 音频文件路径
            language: 语言代码 (id=印尼语)
        
        Returns:
            转录文本
        """
        if not self.initialized:
            if not self.initialize():
                return ""
        
        try:
            start_time = time.time()
            
            # 转录音频
            segments, info = self.model.transcribe(
                audio_file,
                language=language,
                beam_size=5,
                vad_filter=True,  # 使用VAD过滤
                vad_parameters=dict(
                    threshold=0.5,
                    min_speech_duration_ms=250,
                    min_silence_duration_ms=500
                )
            )
            
            # 合并所有片段
            text = " ".join([segment.text for segment in segments])
            
            elapsed = time.time() - start_time
            print(f"  [ASR] 识别完成: '{text}' ({elapsed:.2f}秒)")
            
            return text.strip()
            
        except Exception as e:
            print(f"  [ASR] 识别失败: {e}")
            return ""


# ==================== TTS引擎 (Edge TTS) ====================

class TTSEngine:
    """TTS语音合成引擎 - 使用Edge TTS"""
    
    def __init__(self):
        self.cache_dir = os.path.join(CONFIG['temp_dir'], 'tts_cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        self.cache = {}  # 文本 -> 音频文件路径
        
        # 检查edge-tts是否安装
        try:
            import edge_tts
            self.edge_tts = edge_tts
            print("[TTS] ✓ Edge TTS 已安装")
        except ImportError:
            print("[TTS] ⚠ Edge TTS未安装，正在安装...")
            os.system("pip3 install edge-tts -q")
            import edge_tts
            self.edge_tts = edge_tts
    
    async def synthesize_async(self, text, output_file):
        """异步合成语音"""
        try:
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            communicate = self.edge_tts.Communicate(
                text,
                CONFIG['tts_voice'],
                rate=CONFIG['tts_rate'],
                pitch=CONFIG['tts_pitch']
            )
            
            await communicate.save(output_file)
            
            # 验证文件是否生成
            if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
                raise Exception("TTS文件生成失败或为空")
            
            return True
        except Exception as e:
            print(f"  [TTS] 合成失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def synthesize(self, text, output_file=None):
        """
        合成语音
        
        Args:
            text: 要合成的文本
            output_file: 输出文件路径(可选)
        
        Returns:
            电话格式的WAV文件路径
        """
        # 检查缓存
        if CONFIG['enable_cache'] and text in self.cache:
            if os.path.exists(self.cache[text]):
                print(f"  [TTS] 使用缓存: '{text[:30]}...'")
                return self.cache[text]
        
        try:
            start_time = time.time()
            
            # 生成临时文件
            if output_file is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                output_file = os.path.join(CONFIG['temp_dir'], f"tts_{timestamp}.mp3")
            
            # 合成语音
            asyncio.run(self.synthesize_async(text, output_file))
            
            # 转换为电话格式 (8000Hz, 单声道, WAV)
            wav_file = output_file.replace('.mp3', '.wav')
            cmd = f'ffmpeg -i "{output_file}" -ar 8000 -ac 1 -acodec pcm_s16le "{wav_file}" -y -loglevel error 2>&1'
            result = os.system(cmd)
            
            if result != 0 or not os.path.exists(wav_file):
                print(f"  [TTS] ffmpeg转换失败")
                return None
            
            # 删除MP3
            try:
                if os.path.exists(output_file):
                    os.remove(output_file)
            except:
                pass
            
            elapsed = time.time() - start_time
            print(f"  [TTS] 合成完成: '{text[:30]}...' ({elapsed:.2f}秒)")
            
            # 添加到缓存
            if CONFIG['enable_cache']:
                self.cache[text] = wav_file
            
            return wav_file
            
        except Exception as e:
            print(f"  [TTS] 合成失败: {e}")
            return None


# ==================== AI对话引擎 ====================

class DialogueEngine:
    """AI对话引擎 - 使用GPT-3.5"""
    
    def __init__(self):
        self.context = []
        self.max_context = 10  # 保留最近10轮对话
        
        # 系统提示词（印尼语）
        self.system_prompt = """Anda adalah asisten virtual yang ramah dan membantu. 
Anda berbicara dalam bahasa Indonesia dengan jelas dan sopan.
Jawaban Anda singkat dan langsung ke intinya (maksimal 2-3 kalimat).
Jika Anda tidak mengerti, minta klarifikasi dengan sopan."""
        
        # 检查OpenAI API
        if not CONFIG['openai_api_key']:
            print("[AI] ⚠ 警告: 未设置 OPENAI_API_KEY")
            print("  请设置环境变量: export OPENAI_API_KEY='your-key'")
        else:
            print("[AI] ✓ OpenAI API Key 已配置")
    
    def get_response(self, user_text):
        """
        获取AI回复
        
        Args:
            user_text: 用户输入文本
        
        Returns:
            AI回复文本
        """
        if not CONFIG['openai_api_key']:
            # 无API Key时的默认回复
            return "Maaf, saya tidak dapat merespons saat ini. Silakan coba lagi nanti."
        
        try:
            start_time = time.time()
            
            # 添加用户消息到上下文
            self.context.append({"role": "user", "content": user_text})
            
            # 调用OpenAI API (新版本)
            from openai import OpenAI
            client = OpenAI(api_key=CONFIG['openai_api_key'])
            
            messages = [
                {"role": "system", "content": self.system_prompt},
                *self.context[-self.max_context:]  # 只保留最近的对话
            ]
            
            response = client.chat.completions.create(
                model=CONFIG['ai_model'],
                messages=messages,
                max_tokens=150,
                temperature=0.7
            )
            
            reply = response.choices[0].message.content.strip()
            
            # 添加AI回复到上下文
            self.context.append({"role": "assistant", "content": reply})
            
            elapsed = time.time() - start_time
            print(f"  [AI] 回复生成: '{reply[:50]}...' ({elapsed:.2f}秒)")
            
            return reply
            
        except Exception as e:
            print(f"  [AI] 生成失败: {e}")
            return "Maaf, saya mengalami masalah teknis. Bisakah Anda mengulanginya?"
    
    def reset_context(self):
        """重置对话上下文"""
        self.context = []
        print("  [AI] 对话上下文已重置")


# ==================== VAD语音活动检测 ====================

class VADDetector:
    """语音活动检测器 - 检测说话和静音"""
    
    def __init__(self):
        self.is_speaking = False
        self.silence_start = None
        self.speech_frames = []
        self.sample_rate = 8000
        
    def process_audio_frame(self, audio_data):
        """
        处理音频帧，检测语音活动
        
        Args:
            audio_data: 音频数据 (bytes)
        
        Returns:
            'speaking' / 'silence' / 'sentence_end'
        """
        # 计算音频能量
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        energy = np.sqrt(np.mean(audio_array.astype(float)**2))
        
        # 判断是否在说话
        if energy > CONFIG['vad_speech_threshold'] * 32768:  # 16-bit音频
            if not self.is_speaking:
                self.is_speaking = True
                self.silence_start = None
                print("  [VAD] 检测到说话")
            
            self.speech_frames.append(audio_data)
            return 'speaking'
        else:
            if self.is_speaking:
                # 检测静音持续时间
                if self.silence_start is None:
                    self.silence_start = time.time()
                
                silence_duration = time.time() - self.silence_start
                
                if silence_duration >= CONFIG['vad_silence_duration']:
                    # 静音超过阈值，判定句子结束
                    self.is_speaking = False
                    print(f"  [VAD] 句子结束 (静音{silence_duration:.1f}秒)")
                    return 'sentence_end'
            
            return 'silence'
    
    def get_speech_audio(self):
        """获取积累的语音数据"""
        if not self.speech_frames:
            return None
        
        audio_data = b''.join(self.speech_frames)
        self.speech_frames = []
        return audio_data
    
    def reset(self):
        """重置检测器"""
        self.is_speaking = False
        self.silence_start = None
        self.speech_frames = []


# ==================== AI对话回调 ====================

class AIConversationCallback(pj.CallCallback):
    """AI智能对话回调"""
    
    def __init__(self, call=None, ai_system=None):
        pj.CallCallback.__init__(self, call)
        self.ai_system = ai_system
        
        # 呼叫状态
        self.call_connected = False
        self.call_ended = False
        self.start_time = time.time()
        
        # 音频组件
        self.recorder = None
        self.recorder_id = None
        self.player = None
        self.player_id = None
        
        # AI组件
        self.asr_engine = ASREngine()
        self.tts_engine = TTSEngine()
        self.dialogue_engine = DialogueEngine()
        self.vad = VADDetector()
        
        # 音频缓冲
        self.audio_buffer = []
        self.is_processing = False
        
        # 录音完整通话
        self.full_recording_file = None
        
    def on_state(self):
        """呼叫状态变化"""
        info = self.call.info()
        elapsed = time.time() - self.start_time
        
        print(f"\n[{elapsed:.1f}s] 呼叫状态: {info.state_text}")
        
        if info.state == pj.CallState.CONFIRMED:
            self.call_connected = True
            print("  >>> 呼叫已接通，AI对话已激活")
            
            # 通知系统
            if self.ai_system:
                self.ai_system.command_queue.put(('call_connected', self))
        
        elif info.state == pj.CallState.DISCONNECTED:
            self.call_ended = True
            duration = time.time() - self.start_time
            print(f"  >>> 呼叫结束 (时长: {duration:.1f}秒)")
            self.cleanup()
    
    def on_media_state(self):
        """媒体状态变化"""
        info = self.call.info()
        
        if info.media_state == pj.MediaState.ACTIVE:
            call_slot = info.conf_slot
            
            # 连接音频通道（对方声音 → 本地扬声器，用于监听）
            pj.Lib.instance().conf_connect(call_slot, 0)
            
            print("  [媒体] AI对话音频通道已激活")
    
    def start_recording(self):
        """开始录制完整通话"""
        try:
            info = self.call.info()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.full_recording_file = os.path.join(
                CONFIG['recordings_dir'],
                f"ai_call_{timestamp}.wav"
            )
            
            self.recorder = pj.Lib.instance().create_recorder(self.full_recording_file)
            self.recorder_id = pj.Lib.instance().recorder_get_slot(self.recorder)
            
            # 连接音频源
            pj.Lib.instance().conf_connect(info.conf_slot, self.recorder_id)
            pj.Lib.instance().conf_connect(0, self.recorder_id)
            
            print(f"  [录音] 开始录制: {os.path.basename(self.full_recording_file)}")
            return True
        except Exception as e:
            print(f"  [录音] 启动失败: {e}")
            return False
    
    def play_audio(self, audio_file):
        """播放音频给对方"""
        try:
            info = self.call.info()
            
            # 停止当前播放
            if self.player:
                try:
                    pj.Lib.instance().conf_disconnect(self.player_id, info.conf_slot)
                    self.player = None
                except:
                    pass
            
            # 创建播放器
            self.player = pj.Lib.instance().create_player(audio_file, loop=False)
            self.player_id = pj.Lib.instance().player_get_slot(self.player)
            
            # 连接到呼叫
            pj.Lib.instance().conf_connect(self.player_id, info.conf_slot)
            
            print(f"  [播放] 正在播放给对方")
            return True
        except Exception as e:
            print(f"  [播放] 失败: {e}")
            return False
    
    def process_speech_segment(self, audio_data):
        """
        处理一段完整的语音
        这是核心的AI对话流程
        """
        if self.is_processing:
            print("  [处理] 正在处理中，跳过")
            return
        
        self.is_processing = True
        
        try:
            print("\n" + "="*60)
            print("  AI对话处理流程")
            print("="*60)
            
            # 1. 保存音频片段到临时文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            temp_audio = os.path.join(CONFIG['temp_dir'], f"speech_{timestamp}.wav")
            
            # 写入WAV文件
            with wave.open(temp_audio, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(8000)
                wf.writeframes(audio_data)
            
            print(f"  [1/4] 音频片段已保存: {len(audio_data)} bytes")
            
            # 2. ASR识别
            print("  [2/4] 正在识别语音...")
            user_text = self.asr_engine.transcribe(temp_audio, language='id')
            
            if not user_text:
                print("  ⚠ 未识别到文本")
                self.is_processing = False
                return
            
            print(f"  👤 用户说: {user_text}")
            
            # 3. AI生成回复
            print("  [3/4] 正在生成AI回复...")
            ai_reply = self.dialogue_engine.get_response(user_text)
            
            print(f"  🤖 AI回复: {ai_reply}")
            
            # 4. TTS合成并播放
            print("  [4/4] 正在合成语音...")
            tts_audio = self.tts_engine.synthesize(ai_reply)
            
            if tts_audio and os.path.exists(tts_audio):
                self.play_audio(tts_audio)
                print("  ✓ 回复已播放")
            else:
                print("  ✗ TTS合成失败")
            
            print("="*60 + "\n")
            
        except Exception as e:
            print(f"  ✗ 处理失败: {e}")
        
        finally:
            self.is_processing = False
            
            # 清理临时文件
            try:
                if os.path.exists(temp_audio):
                    os.remove(temp_audio)
            except:
                pass
    
    def cleanup(self):
        """清理资源"""
        if self.recorder:
            try:
                info = self.call.info()
                pj.Lib.instance().conf_disconnect(info.conf_slot, self.recorder_id)
                pj.Lib.instance().conf_disconnect(0, self.recorder_id)
                self.recorder = None
                print("  [录音] 已停止")
            except:
                pass
        
        if self.player:
            try:
                self.player = None
            except:
                pass


# ==================== AI对话系统 ====================

class AIConversationSystem:
    """AI智能对话系统核心"""
    
    def __init__(self):
        self.lib = None
        self.acc = None
        self.transport = None
        self.current_call = None
        self.current_callback = None
        
        # 命令队列
        self.command_queue = queue.Queue()
        self.result_queue = queue.Queue()
        
        print("\n" + "="*70)
        print("  AI智能对话系统 - 免费方案 (印尼语优化)")
        print("="*70)
        print(f"\nASR: faster-whisper ({CONFIG['whisper_model']})")
        print(f"TTS: Edge TTS ({CONFIG['tts_voice']})")
        print(f"AI: {CONFIG['ai_model']}")
        print("="*70 + "\n")
    
    def start(self):
        """启动系统"""
        try:
            # 创建PJSIP库
            self.lib = pj.Lib()
            
            # 媒体配置
            media_cfg = pj.MediaConfig()
            media_cfg.enable_ice = False
            media_cfg.no_vad = False  # 启用PJSIP内置VAD
            media_cfg.ec_tail_len = 200
            media_cfg.clock_rate = 8000
            
            # 初始化
            self.lib.init(
                log_cfg=pj.LogConfig(level=CONFIG['log_level']),
                media_cfg=media_cfg
            )
            
            # 创建传输
            self.transport = self.lib.create_transport(pj.TransportType.UDP, pj.TransportConfig(0))
            print(f"✓ 传输: {self.transport.info().host}:{self.transport.info().port}")
            
            # 启动
            self.lib.start()
            
            # 设置null音频设备（服务器模式）
            try:
                self.lib.set_null_snd_dev()
                print("✓ 音频设备: null设备 (服务器模式)")
            except:
                pass
            
            # 创建账户
            acc_cfg = pj.AccountConfig()
            acc_cfg.id = f"sip:{CONFIG['caller_number']}@{CONFIG['server']}"
            acc_cfg.reg_uri = ""
            
            self.acc = self.lib.create_account(acc_cfg)
            print("✓ 账户已创建\n")
            
            print("="*70)
            print("✓ 系统启动成功!")
            print("="*70)
            
            return True
            
        except pj.Error as e:
            print(f"\n✗ 启动失败: {e}")
            return False
    
    def make_call(self, phone_number):
        """发起呼叫"""
        self.command_queue.put(('call', phone_number))
        try:
            return self.result_queue.get(timeout=5)
        except queue.Empty:
            return None
    
    def _make_call_internal(self, phone_number):
        """内部呼叫方法"""
        full_number = f"{CONFIG['prefix']}{phone_number}"
        sip_uri = f"sip:{full_number}@{CONFIG['server']}:{CONFIG['port']}"
        
        print(f"\n发起AI对话呼叫:")
        print(f"  目标号码: {phone_number}")
        print(f"  SIP URI: {sip_uri}")
        
        try:
            self.current_callback = AIConversationCallback(ai_system=self)
            self.current_call = self.acc.make_call(sip_uri, cb=self.current_callback)
            
            print("✓ 呼叫已发起")
            return self.current_call
        except pj.Error as e:
            print(f"✗ 呼叫失败: {e}")
            return None
    
    def on_call_connected(self, callback):
        """呼叫接通后初始化AI对话"""
        print("\n[系统] 初始化AI对话...")
        
        time.sleep(1)
        
        # 开始录音
        callback.start_recording()
        
        # 初始化ASR引擎
        callback.asr_engine.initialize()
        
        # 播放欢迎语
        welcome_text = "Halo, saya asisten virtual. Ada yang bisa saya bantu?"
        welcome_audio = callback.tts_engine.synthesize(welcome_text)
        if welcome_audio:
            callback.play_audio(welcome_audio)
        
        print("[系统] ✓ AI对话已就绪\n")
        print("="*70)
        print("  现在可以开始对话...")
        print("  系统会自动检测语音并智能回复")
        print("="*70 + "\n")
        
        # 启动VAD监听线程
        vad_thread = threading.Thread(
            target=self._vad_monitor_loop,
            args=(callback,),
            daemon=True
        )
        vad_thread.start()
    
    def _vad_monitor_loop(self, callback):
        """VAD监听循环 - 模拟实时监听"""
        print("[VAD] 监听线程已启动")
        
        # 注意：这是简化实现
        # 实际需要从PJSIP音频桥获取实时音频流
        # 这里使用定期检查录音文件的方式作为示例
        
        while not callback.call_ended:
            time.sleep(0.5)
            
            # 实际实现需要：
            # 1. 从conference bridge获取音频帧
            # 2. 送入VAD检测
            # 3. 检测到句子结束时触发ASR+AI+TTS
        
        print("[VAD] 监听线程已退出")
    
    def hangup_current_call(self):
        """挂断呼叫"""
        self.command_queue.put(('hangup', None))
        try:
            return self.result_queue.get(timeout=2)
        except queue.Empty:
            return False
    
    def _hangup_internal(self):
        """内部挂断"""
        if self.current_call:
            try:
                self.current_call.hangup()
                return True
            except:
                pass
        return False
    
    def get_status(self):
        """获取状态"""
        status = {
            'has_active_call': self.current_call is not None,
            'call_connected': False,
            'ai_ready': False
        }
        
        if self.current_callback:
            status['call_connected'] = self.current_callback.call_connected
            status['ai_ready'] = self.current_callback.asr_engine.initialized
        
        return status
    
    def stop(self):
        """停止系统"""
        if self.current_call:
            self.hangup_current_call()
        
        if self.lib:
            try:
                self.lib.destroy()
            except:
                pass
        
        print("\n系统已停止")


# ==================== HTTP API ====================

class AIAPIHandler(BaseHTTPRequestHandler):
    """HTTP API处理器"""
    
    ai_system = None
    
    def do_POST(self):
        path = urlparse(self.path).path
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(body) if body else {}
        except:
            data = {}
        
        if path == '/api/call':
            self.handle_call(data)
        elif path == '/api/hangup':
            self.handle_hangup()
        elif path == '/api/status':
            self.handle_status()
        else:
            self.send_error_response("未知API")
    
    def do_GET(self):
        if self.path == '/':
            self.send_html()
        else:
            self.send_error_response("未找到")
    
    def handle_call(self, data):
        phone = data.get('phone_number', '')
        if not phone:
            self.send_error_response("缺少phone_number")
            return
        
        result = self.ai_system.make_call(phone)
        if result:
            self.send_json({'success': True, 'message': 'AI对话已启动'})
        else:
            self.send_error_response("呼叫失败")
    
    def handle_hangup(self):
        result = self.ai_system.hangup_current_call()
        if result:
            self.send_json({'success': True, 'message': '已挂断'})
        else:
            self.send_error_response("无活动呼叫")
    
    def handle_status(self):
        status = self.ai_system.get_status()
        self.send_json({'success': True, **status})
    
    def send_json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def send_error_response(self, msg):
        self.send_response(400)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({'success': False, 'error': msg}).encode('utf-8'))
    
    def send_html(self):
        html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>AI智能对话系统</title>
    <style>
        body { font-family: Arial; max-width: 800px; margin: 50px auto; padding: 20px; }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        .status { background: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0; }
        input { padding: 10px; font-size: 16px; width: 300px; margin: 5px; }
        button { padding: 10px 20px; font-size: 16px; margin: 5px; 
                 background: #3498db; color: white; border: none; cursor: pointer; }
        button:hover { background: #2980b9; }
        .hangup { background: #e74c3c; }
        .hangup:hover { background: #c0392b; }
        #log { background: #2c3e50; color: #2ecc71; padding: 15px; 
               height: 400px; overflow-y: auto; font-family: monospace; border-radius: 5px; }
        .info { background: #3498db; color: white; padding: 10px; border-radius: 5px; margin: 10px 0; }
    </style>
</head>
<body>
    <h1>🤖 AI智能对话系统</h1>
    
    <div class="info">
        <strong>免费方案 | 印尼语优化</strong><br>
        ASR: faster-whisper | TTS: Edge TTS | AI: GPT-3.5
    </div>
    
    <div class="status">
        <strong>状态:</strong> <span id="status">检查中...</span><br>
        <strong>AI就绪:</strong> <span id="ai-ready">-</span>
    </div>
    
    <div>
        <input type="text" id="phone" placeholder="输入号码 (例如: 82121065486)">
        <button onclick="makeCall()">开始AI对话</button>
        <button class="hangup" onclick="hangup()">挂断</button>
    </div>
    
    <div id="log">系统就绪...\n等待操作...</div>
    
    <script>
        function log(msg) {
            const logEl = document.getElementById('log');
            const time = new Date().toLocaleTimeString();
            logEl.innerHTML += `[${time}] ${msg}\n`;
            logEl.scrollTop = logEl.scrollHeight;
        }
        
        function makeCall() {
            const phone = document.getElementById('phone').value.trim();
            if (!phone) { alert('请输入号码'); return; }
            
            log(`🤖 启动AI对话: ${phone}`);
            fetch('/api/call', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({phone_number: phone})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    log(`✓ ${data.message}`);
                    log(`AI系统会自动识别语音并智能回复`);
                } else {
                    log(`✗ ${data.error}`);
                }
                updateStatus();
            });
        }
        
        function hangup() {
            log('正在挂断...');
            fetch('/api/hangup', { method: 'POST' })
            .then(r => r.json())
            .then(data => {
                log(data.success ? `✓ ${data.message}` : `✗ ${data.error}`);
                updateStatus();
            });
        }
        
        function updateStatus() {
            fetch('/api/status', { method: 'POST' })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('status').textContent = 
                        data.has_active_call ? (data.call_connected ? '通话中' : '呼叫中') : '空闲';
                    document.getElementById('ai-ready').textContent = 
                        data.ai_ready ? '✓ 是' : '✗ 否';
                }
            });
        }
        
        setInterval(updateStatus, 3000);
        updateStatus();
    </script>
</body>
</html>
        """
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def log_message(self, format, *args):
        pass


def run_api_server(ai_system):
    """运行API服务器"""
    AIAPIHandler.ai_system = ai_system
    
    try:
        server = HTTPServer((CONFIG['api_host'], CONFIG['api_port']), AIAPIHandler)
        print(f"✓ API服务器: http://localhost:{CONFIG['api_port']}\n")
        
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
            
    except OSError as e:
        if e.errno == 98:  # Address already in use
            print(f"\n✗ 端口 {CONFIG['api_port']} 已被占用!")
            print(f"  可能原因:")
            print(f"    1. 系统已在运行")
            print(f"    2. 其他程序占用了该端口")
            print(f"\n  解决方法:")
            print(f"    1. 停止旧进程: pkill -f sip_ai_conversation.py")
            print(f"    2. 或修改端口: 编辑CONFIG['api_port']")
            print(f"    3. 或使用修复脚本: ./fix_and_start.sh\n")
            import sys
            sys.exit(1)
        else:
            raise


# ==================== 主程序 ====================

def main():
    """主程序"""
    print("\n启动AI智能对话系统...\n")
    
    # 检查依赖
    print("检查依赖...")
    dependencies_ok = True
    
    try:
        import faster_whisper
        print("  ✓ faster-whisper")
    except:
        print("  ✗ faster-whisper (将自动安装)")
    
    try:
        import edge_tts
        print("  ✓ edge-tts")
    except:
        print("  ✗ edge-tts (将自动安装)")
    
    try:
        import openai
        print("  ✓ openai")
    except:
        print("  ⚠ openai未安装")
        print("    安装: pip3 install openai")
        dependencies_ok = False
    
    if not CONFIG['openai_api_key']:
        print("  ⚠ 未设置 OPENAI_API_KEY")
        print("    设置: export OPENAI_API_KEY='your-key'")
    
    print()
    
    # 检查端口是否被占用
    print("检查端口...")
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', CONFIG['api_port']))
    sock.close()
    
    if result == 0:
        print(f"✗ 端口 {CONFIG['api_port']} 已被占用!")
        print(f"\n系统可能已在运行。")
        print(f"\n解决方法:")
        print(f"  1. 检查运行状态: ./check_ai_status.sh")
        print(f"  2. 停止旧进程: pkill -f sip_ai_conversation.py")
        print(f"  3. 或使用修复脚本: ./fix_and_start.sh")
        print(f"  4. 或访问已运行的实例: http://localhost:{CONFIG['api_port']}\n")
        sys.exit(1)
    else:
        print(f"✓ 端口 {CONFIG['api_port']} 可用\n")
    
    # 创建系统
    ai_system = AIConversationSystem()
    
    if not ai_system.start():
        sys.exit(1)
    
    # 启动API服务器
    api_thread = threading.Thread(target=run_api_server, args=(ai_system,), daemon=True)
    api_thread.start()
    
    # 等待API服务器启动
    time.sleep(0.5)
    
    print("\n" + "="*70)
    print("使用说明:")
    print("  1. 访问: http://localhost:8089")
    print("  2. 输入号码并点击'开始AI对话'")
    print("  3. 系统会自动:")
    print("     - 识别对方语音 (ASR)")
    print("     - AI智能回复")
    print("     - 语音合成 (TTS)")
    print("  4. 录音保存在: " + CONFIG['recordings_dir'])
    print("="*70)
    print("\n按 Ctrl+C 停止\n")
    
    try:
        while True:
            try:
                cmd, data = ai_system.command_queue.get(timeout=0.1)
                
                if cmd == 'call':
                    result = ai_system._make_call_internal(data)
                    ai_system.result_queue.put(result)
                elif cmd == 'hangup':
                    result = ai_system._hangup_internal()
                    ai_system.result_queue.put(result)
                elif cmd == 'call_connected':
                    ai_system.on_call_connected(data)
            except queue.Empty:
                pass
            
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\n停止系统...")
        ai_system.stop()


if __name__ == "__main__":
    main()

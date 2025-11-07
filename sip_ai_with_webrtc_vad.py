#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI对话系统 - 使用WebRTC VAD实现真正的语音检测
方案：录音+实时读取+WebRTC VAD检测
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
import webrtcvad
from datetime import datetime
from collections import deque

# 配置
CONFIG = {
    'server': '147.139.205.88',
    'port': 5060,
    'caller_number': '6281479242434',
    'prefix': '13462',
    'log_level': 3,
    
    'audio_dir': '/home/henry/pjproject/audio_files',
    'recordings_dir': '/home/henry/pjproject/recordings',
    'temp_dir': '/home/henry/pjproject/temp_audio',
    
    'api_host': '0.0.0.0',
    'api_port': 8090,
    
    'openai_api_key': os.getenv('OPENAI_API_KEY', ''),
    'ai_model': 'gpt-3.5-turbo',
    
    'whisper_model': 'base',
    'whisper_device': 'cpu',
    'whisper_compute_type': 'int8',
    
    'tts_voice': 'id-ID-ArdiNeural',
    
    # WebRTC VAD配置
    'vad_aggressiveness': 2,  # 0-3，3最激进
    'vad_frame_duration': 30,  # ms, 可选10/20/30
    'vad_silence_frames': 20,  # 连续静音帧数判定句子结束
    'vad_min_speech_frames': 5,  # 最少语音帧数
}

for d in [CONFIG['temp_dir'], CONFIG['recordings_dir'], CONFIG['audio_dir']]:
    os.makedirs(d, exist_ok=True)


# ==================== WebRTC VAD检测器 ====================

class WebRTCVADDetector:
    """使用WebRTC VAD的语音检测器"""
    
    def __init__(self, aggressiveness=2, frame_duration=30):
        """
        aggressiveness: 0-3, 越高越激进（更容易判定为静音）
        frame_duration: 帧长度(ms), 必须是10/20/30
        """
        self.vad = webrtcvad.Vad(aggressiveness)
        self.frame_duration = frame_duration
        self.sample_rate = 8000  # WebRTC VAD只支持8000/16000/32000/48000
        
        # 帧大小（字节）
        self.frame_size = int(self.sample_rate * self.frame_duration / 1000) * 2  # *2因为16-bit
        
        # 状态
        self.is_speaking = False
        self.speech_frames = []
        self.silence_count = 0
        
        # 配置
        self.silence_threshold = CONFIG['vad_silence_frames']
        self.min_speech_frames = CONFIG['vad_min_speech_frames']
        
        print(f"[VAD] WebRTC VAD初始化")
        print(f"  激进度: {aggressiveness} (0=宽容, 3=严格)")
        print(f"  帧长: {frame_duration}ms")
        print(f"  帧大小: {self.frame_size}字节")
        print(f"  静音阈值: {self.silence_threshold}帧")
    
    def process_audio(self, audio_data):
        """
        处理音频数据
        返回: None 或 ('speech_complete', audio_bytes)
        """
        # 将音频分成固定大小的帧
        offset = 0
        
        while offset + self.frame_size <= len(audio_data):
            frame = audio_data[offset:offset + self.frame_size]
            
            try:
                # WebRTC VAD检测
                is_speech = self.vad.is_speech(frame, self.sample_rate)
                
                if is_speech:
                    # 检测到语音
                    if not self.is_speaking:
                        self.is_speaking = True
                        self.speech_frames = []
                        self.silence_count = 0
                        print("  [VAD] 🎤 检测到说话")
                    
                    self.speech_frames.append(frame)
                    self.silence_count = 0
                    
                else:
                    # 静音帧
                    if self.is_speaking:
                        self.speech_frames.append(frame)  # 也保存静音帧
                        self.silence_count += 1
                        
                        # 判断是否句子结束
                        if self.silence_count >= self.silence_threshold:
                            speech_frame_count = len(self.speech_frames) - self.silence_count
                            
                            if speech_frame_count >= self.min_speech_frames:
                                print(f"  [VAD] ✓ 句子结束 (帧数:{speech_frame_count}, 静音:{self.silence_count})")
                                
                                # 合并所有帧
                                complete_audio = b''.join(self.speech_frames)
                                
                                # 重置状态
                                self.is_speaking = False
                                self.speech_frames = []
                                self.silence_count = 0
                                
                                return ('speech_complete', complete_audio)
                            else:
                                # 语音太短，忽略
                                print(f"  [VAD] ⚠ 忽略短语音 (帧数:{speech_frame_count})")
                                self.is_speaking = False
                                self.speech_frames = []
                                self.silence_count = 0
            
            except Exception as e:
                print(f"  [VAD] 处理错误: {e}")
            
            offset += self.frame_size
        
        return None
    
    def reset(self):
        """重置状态"""
        self.is_speaking = False
        self.speech_frames = []
        self.silence_count = 0


# ==================== 实时录音文件读取器 ====================

class RealtimeWavReader:
    """实时读取正在录制的WAV文件"""
    
    def __init__(self, wav_filename):
        self.filename = wav_filename
        self.last_position = 44  # 跳过WAV头部（44字节）
        self.sample_rate = 8000
        self.sample_width = 2  # 16-bit
        
    def read_new_data(self):
        """读取新增的音频数据"""
        try:
            if not os.path.exists(self.filename):
                return None
            
            # 直接读取原始文件（不用wave模块，因为PJSIP录音时WAV头不完整）
            file_size = os.path.getsize(self.filename)
            
            if file_size <= self.last_position:
                return None  # 没有新数据
            
            with open(self.filename, 'rb') as f:
                f.seek(self.last_position)
                new_data = f.read()
                
                if len(new_data) > 0:
                    self.last_position = file_size
                    return new_data
                
            return None
        
        except Exception as e:
            # print(f"  [读取] 错误: {e}")
            return None


# ==================== ASR引擎 ====================

class ASREngine:
    def __init__(self):
        self.model = None
    
    def initialize(self):
        if self.model:
            return True
        try:
            print("[ASR] 加载Whisper模型...")
            from faster_whisper import WhisperModel
            self.model = WhisperModel(
                CONFIG['whisper_model'],
                device=CONFIG['whisper_device'],
                compute_type=CONFIG['whisper_compute_type']
            )
            print("  ✓ ASR就绪")
            return True
        except Exception as e:
            print(f"  ✗ {e}")
            return False
    
    def transcribe(self, audio_file):
        if not self.model:
            if not self.initialize():
                return ""
        
        try:
            start = time.time()
            segments, _ = self.model.transcribe(audio_file, language='id', vad_filter=False)
            text = " ".join([s.text for s in segments]).strip()
            elapsed = time.time() - start
            
            if text:
                print(f"  [ASR] '{text}' ({elapsed:.1f}s)")
            return text
        except Exception as e:
            print(f"  [ASR] 错误: {e}")
            return ""


# ==================== TTS引擎 ====================

class TTSEngine:
    def __init__(self):
        # 尝试导入Edge TTS
        try:
            import edge_tts
            self.edge_tts = edge_tts
            self.use_edge = True
        except:
            self.edge_tts = None
            self.use_edge = False
        
        # 检查espeak作为本地备份
        self.espeak_available = os.system("which espeak >/dev/null 2>&1") == 0
        
        if self.espeak_available:
            print("[TTS] 本地espeak可用（备选方案）")
        else:
            print("[TTS] 正在安装espeak...")
            os.system("sudo apt-get install -y espeak >/dev/null 2>&1")
            self.espeak_available = os.system("which espeak >/dev/null 2>&1") == 0
    
    async def _synthesize(self, text, output_file):
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Edge TTS有时不稳定，直接跳过使用espeak
        # 取消注释下面的代码来尝试Edge TTS:
        """
        max_retries = 2
        for attempt in range(max_retries):
            try:
                comm = self.edge_tts.Communicate(text, CONFIG['tts_voice'])
                await comm.save(output_file)
                
                # 验证文件
                if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
                    return True
                else:
                    raise Exception("生成的音频文件太小或为空")
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5)
                    continue
                else:
                    raise e
        """
        # 暂时禁用Edge TTS
        raise Exception("Edge TTS已禁用，使用本地espeak")
    
    def synthesize_espeak(self, text):
        """使用espeak本地TTS"""
        try:
            start = time.time()
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            wav = os.path.join(CONFIG['temp_dir'], f"tts_espeak_{ts}.wav")
            
            # 使用espeak合成
            # -v id: 印尼语
            # -s 150: 语速150
            # -w: 输出WAV文件
            cmd = f'espeak -v id -s 150 -w "{wav}.tmp" "{text}" 2>/dev/null'
            result = os.system(cmd)
            
            if result != 0:
                return None
            
            # 转换为8000Hz电话格式
            cmd2 = f'ffmpeg -i "{wav}.tmp" -ar 8000 -ac 1 "{wav}" -y -loglevel error 2>&1'
            result2 = os.system(cmd2)
            
            # 删除临时文件
            try:
                os.remove(f"{wav}.tmp")
            except:
                pass
            
            if result2 != 0 or not os.path.exists(wav):
                return None
            
            elapsed = time.time() - start
            print(f"  [TTS] espeak完成 ({elapsed:.1f}s)")
            return wav
            
        except Exception as e:
            print(f"  [TTS] espeak失败: {e}")
            return None
    
    def synthesize(self, text):
        # 首先尝试Edge TTS
        if self.use_edge and self.edge_tts:
            try:
                start = time.time()
                ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                mp3 = os.path.join(CONFIG['temp_dir'], f"tts_{ts}.mp3")
                
                asyncio.run(self._synthesize(text, mp3))
                
                if not os.path.exists(mp3) or os.path.getsize(mp3) == 0:
                    raise Exception("未生成音频")
                
                wav = mp3.replace('.mp3', '.wav')
                result = os.system(f'ffmpeg -i "{mp3}" -ar 8000 -ac 1 "{wav}" -y -loglevel error 2>&1')
                
                if result != 0 or not os.path.exists(wav):
                    raise Exception("转换失败")
                
                try:
                    os.remove(mp3)
                except:
                    pass
                
                elapsed = time.time() - start
                print(f"  [TTS] Edge TTS完成 ({elapsed:.1f}s)")
                return wav
                
            except Exception as e:
                print(f"  [TTS] Edge TTS失败: {e}")
                # 继续尝试espeak
        
        # 备选方案：使用espeak
        if self.espeak_available:
            print(f"  [TTS] 使用本地espeak...")
            return self.synthesize_espeak(text)
        
        # 都失败了
        print(f"  [TTS] ⚠ 所有TTS方案都失败")
        return None


# ==================== AI引擎 ====================

class AIEngine:
    def __init__(self):
        self.context = []
        self.prompt = "Anda adalah asisten virtual yang ramah. Jawaban singkat (maks 2 kalimat) dalam bahasa Indonesia."
    
    def get_response(self, user_text):
        if not CONFIG['openai_api_key']:
            return "Maaf, layanan tidak tersedia."
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=CONFIG['openai_api_key'])
            
            self.context.append({"role": "user", "content": user_text})
            
            start = time.time()
            resp = client.chat.completions.create(
                model=CONFIG['ai_model'],
                messages=[{"role": "system", "content": self.prompt}, *self.context[-10:]],
                max_tokens=150
            )
            
            reply = resp.choices[0].message.content.strip()
            self.context.append({"role": "assistant", "content": reply})
            
            elapsed = time.time() - start
            print(f"  [AI] '{reply}' ({elapsed:.1f}s)")
            return reply
        except Exception as e:
            print(f"  [AI] 错误: {e}")
            return "Maaf, saya tidak mengerti."


# ==================== VAD通话回调 ====================

class VADCallCallback(pj.CallCallback):
    """集成WebRTC VAD的通话回调"""
    
    def __init__(self, call=None, system=None):
        pj.CallCallback.__init__(self, call)
        self.system = system
        self.connected = False
        
        # 组件
        self.asr = ASREngine()
        self.tts = TTSEngine()
        self.ai = AIEngine()
        self.vad = WebRTCVADDetector(
            aggressiveness=CONFIG['vad_aggressiveness'],
            frame_duration=CONFIG['vad_frame_duration']
        )
        
        # 录音
        self.recorder = None
        self.recorder_id = None
        self.record_file = None
        self.wav_reader = None
        
        # 播放
        self.player = None
        self.player_id = None
        
        # VAD线程
        self.vad_running = False
        self.vad_thread = None
        self.is_processing = False
    
    def on_state(self):
        info = self.call.info()
        print(f"\n[呼叫] {info.state_text}")
        
        if info.state == pj.CallState.CONFIRMED:
            self.connected = True
            print("  ✓ 接通")
            if self.system:
                self.system.command_queue.put(('connected', self))
        
        elif info.state == pj.CallState.DISCONNECTED:
            print("  ✓ 通话结束，清理资源...")
            self.connected = False  # 先设置为False，停止VAD循环
            self.cleanup()
    
    def on_media_state(self):
        info = self.call.info()
        if info.media_state == pj.MediaState.ACTIVE:
            pj.Lib.instance().conf_connect(info.conf_slot, 0)
            print("  [媒体] 激活")
    
    def start_vad_recording(self):
        """开始VAD录音 - 双向录制（客户+AI）"""
        try:
            info = self.call.info()
            
            # 创建录音文件
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.record_file = os.path.join(CONFIG['recordings_dir'], f"vad_{ts}.wav")
            
            # 创建PJSIP录音器
            self.recorder = pj.Lib.instance().create_recorder(self.record_file)
            self.recorder_id = pj.Lib.instance().recorder_get_slot(self.recorder)
            
            # 连接双向音频到录音器
            # 1. 客户的声音（远端）
            pj.Lib.instance().conf_connect(info.conf_slot, self.recorder_id)
            # 2. 本地播放的声音（AI回复） - 从slot 0连接
            pj.Lib.instance().conf_connect(0, self.recorder_id)
            
            print(f"  [录音] 开始双向录制: {os.path.basename(self.record_file)}")
            
            # 创建实时读取器
            time.sleep(0.8)  # 等待文件创建和初始化
            self.wav_reader = RealtimeWavReader(self.record_file)
            
            print(f"  [VAD] 开始监控文件: {self.record_file}")
            
            # 启动VAD监听线程
            self.vad_running = True
            self.vad_thread = threading.Thread(target=self._vad_loop, daemon=True)
            self.vad_thread.start()
            
            print("  [VAD] ✓ 监听启动")
            
            return True
        except Exception as e:
            print(f"  [VAD] 启动失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _vad_loop(self):
        """VAD主循环 - 实时读取并检测"""
        print("[VAD] 线程运行中...")
        
        data_received_count = 0
        no_data_count = 0
        
        while self.vad_running and self.connected:
            try:
                # 检查退出条件
                if not self.vad_running or not self.connected:
                    print("[VAD] 收到退出信号")
                    break
                
                # 从录音文件读取新数据
                new_data = self.wav_reader.read_new_data()
                
                if new_data and len(new_data) > 0:
                    data_received_count += 1
                    no_data_count = 0
                    
                    # 每收到100次数据，打印一次进度
                    if data_received_count % 100 == 1:
                        print(f"  [VAD] 已接收 {len(new_data)} 字节音频数据...")
                    
                    # 送给VAD处理
                    result = self.vad.process_audio(new_data)
                    
                    if result:
                        event_type, audio_data = result
                        
                        if event_type == 'speech_complete':
                            # 检测到完整句子，处理它
                            if not self.is_processing:
                                threading.Thread(
                                    target=self._process_speech,
                                    args=(audio_data,),
                                    daemon=True
                                ).start()
                else:
                    # 没有新数据
                    no_data_count += 1
                    # 如果连续50次(2.5秒)没有数据且连接已断开，退出
                    if no_data_count > 50 and not self.connected:
                        print("[VAD] 无新数据且连接已断开，退出")
                        break
                
                # 短暂休眠
                time.sleep(0.05)
                
            except Exception as e:
                # 如果是文件不存在或连接断开，正常退出
                if not self.connected or not self.vad_running:
                    print("[VAD] 连接已断开，正常退出")
                    break
                
                print(f"  [VAD] 错误: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(0.5)
        
        print(f"[VAD] 线程退出 (共处理 {data_received_count} 次数据)")
    
    def _process_speech(self, audio_data):
        """处理检测到的语音"""
        self.is_processing = True
        
        # 注册当前线程到PJLIB
        try:
            pj.Lib.instance().thread_register("vad_worker")
        except Exception as e:
            # 线程已注册或注册失败
            pass
        
        try:
            print("\n" + "="*60)
            print("  🎤 处理语音")
            print("="*60)
            
            # 保存为临时文件
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            temp_wav = os.path.join(CONFIG['temp_dir'], f"speech_{ts}.wav")
            
            with wave.open(temp_wav, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(8000)
                wf.writeframes(audio_data)
            
            # ASR
            print("  [1/3] ASR识别...")
            text = self.asr.transcribe(temp_wav)
            
            if not text:
                print("  ⚠ 未识别")
                return
            
            print(f"  👤 用户: {text}")
            
            # AI
            print("  [2/3] AI生成...")
            reply = self.ai.get_response(text)
            print(f"  🤖 AI: {reply}")
            
            # TTS
            print("  [3/3] TTS合成...")
            audio = self.tts.synthesize(reply)
            
            if audio:
                self.play_audio(audio)
                print("  ✓ 已播放")
            else:
                print("  ⚠ TTS失败，无法播放回复")
                print(f"  💬 文字回复: {reply}")
            
            print("="*60 + "\n")
            
        except Exception as e:
            print(f"  ✗ 处理失败: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_processing = False
            try:
                if os.path.exists(temp_wav):
                    os.remove(temp_wav)
            except:
                pass
    
    def play_audio(self, audio_file):
        """播放音频"""
        try:
            info = self.call.info()
            
            # 停止旧播放器
            if self.player:
                try:
                    pj.Lib.instance().conf_disconnect(self.player_id, info.conf_slot)
                except:
                    pass
            
            # 创建播放器
            self.player = pj.Lib.instance().create_player(audio_file, loop=False)
            self.player_id = pj.Lib.instance().player_get_slot(self.player)
            pj.Lib.instance().conf_connect(self.player_id, info.conf_slot)
            
        except Exception as e:
            print(f"  [播放] 失败: {e}")
    
    def cleanup(self):
        """清理资源"""
        print("  [清理] 停止VAD线程...")
        self.vad_running = False
        self.connected = False
        
        # 等待VAD线程退出
        if self.vad_thread and self.vad_thread.is_alive():
            print("  [清理] 等待VAD线程退出...")
            self.vad_thread.join(timeout=2.0)
            if self.vad_thread.is_alive():
                print("  [清理] ⚠ VAD线程未能及时退出")
            else:
                print("  [清理] ✓ VAD线程已退出")
        
        # 断开并销毁录音器
        if self.recorder:
            try:
                print("  [清理] 断开录音器...")
                info = self.call.info()
                # 断开双向录音连接
                pj.Lib.instance().conf_disconnect(info.conf_slot, self.recorder_id)
                pj.Lib.instance().conf_disconnect(0, self.recorder_id)
                
                # 销毁录音器
                print("  [清理] 销毁录音器...")
                pj.Lib.instance().recorder_destroy(self.recorder)
                self.recorder = None
                print("  [清理] ✓ 录音器已清理")
            except Exception as e:
                print(f"  [清理] 录音器清理错误: {e}")
        
        # 停止播放器
        if self.player:
            try:
                print("  [清理] 停止播放器...")
                pj.Lib.instance().player_destroy(self.player)
                self.player = None
                print("  [清理] ✓ 播放器已清理")
            except Exception as e:
                print(f"  [清理] 播放器清理错误: {e}")
        
        print("  [清理] ✓ 所有资源已清理")


# ==================== 系统核心 ====================

class AISystem:
    def __init__(self):
        self.lib = None
        self.acc = None
        self.current_call = None
        self.command_queue = queue.Queue()
        self.result_queue = queue.Queue()
    
    def start(self):
        try:
            self.lib = pj.Lib()
            
            media_cfg = pj.MediaConfig()
            media_cfg.clock_rate = 8000
            media_cfg.channel_count = 1
            
            self.lib.init(
                log_cfg=pj.LogConfig(level=CONFIG['log_level']),
                media_cfg=media_cfg
            )
            
            self.transport = self.lib.create_transport(pj.TransportType.UDP, pj.TransportConfig(0))
            self.lib.start()
            self.lib.set_null_snd_dev()
            
            acc_cfg = pj.AccountConfig()
            acc_cfg.id = f"sip:{CONFIG['caller_number']}@{CONFIG['server']}"
            acc_cfg.reg_uri = ""
            self.acc = self.lib.create_account(acc_cfg)
            
            print("✓ 系统启动")
            print(f"✓ 传输: {self.transport.info().host}:{self.transport.info().port}")
            return True
        except Exception as e:
            print(f"✗ 启动失败: {e}")
            return False
    
    def make_call(self, phone):
        self.command_queue.put(('call', phone))
        try:
            return self.result_queue.get(timeout=5)
        except:
            return None
    
    def _make_call_internal(self, phone):
        full = f"{CONFIG['prefix']}{phone}"
        uri = f"sip:{full}@{CONFIG['server']}:{CONFIG['port']}"
        
        print(f"\n拨号: {phone}")
        try:
            cb = VADCallCallback(system=self)
            self.current_call = self.acc.make_call(uri, cb=cb)
            return self.current_call
        except Exception as e:
            print(f"✗ {e}")
            return None
    
    def on_connected(self, callback):
        """接通后初始化"""
        print("\n[系统] 初始化...")
        
        # 注册当前线程（如果需要）
        try:
            pj.Lib.instance().thread_register("init_thread")
        except:
            pass
        
        time.sleep(1)
        
        # 初始化ASR
        callback.asr.initialize()
        
        # 启动VAD
        callback.start_vad_recording()
        
        # 播放欢迎语
        print("[系统] 尝试播放欢迎语...")
        welcome = callback.tts.synthesize("Halo, saya asisten virtual. Silakan berbicara.")
        if welcome:
            callback.play_audio(welcome)
            print("[系统] ✓ 欢迎语已播放")
        else:
            print("[系统] ⚠ 欢迎语TTS失败，但VAD仍会工作")
        
        print("[系统] ✓ 就绪，等待语音输入...")


def main():
    print("\n" + "="*70)
    print("  AI对话系统 - WebRTC VAD版本")
    print("="*70)
    print("\nWebRTC VAD: Google的高质量语音检测算法")
    print("="*70 + "\n")
    
    system = AISystem()
    
    if not system.start():
        sys.exit(1)
    
    print("\n命令:")
    print("  call <号码> - 拨打电话")
    print("  quit       - 退出")
    print()
    
    # 启动输入线程
    def input_thread():
        while True:
            try:
                cmd = input(">>> ").strip()
                if not cmd:
                    continue
                
                parts = cmd.split()
                if parts[0] == 'call' and len(parts) >= 2:
                    phone = parts[1]
                    system.command_queue.put(('call', phone))
                elif parts[0] == 'quit':
                    print("退出...")
                    os._exit(0)
                else:
                    print("无效命令")
            except:
                break
    
    threading.Thread(target=input_thread, daemon=True).start()
    
    # 主循环
    try:
        while True:
            try:
                cmd, data = system.command_queue.get(timeout=0.1)
                
                if cmd == 'call':
                    result = system._make_call_internal(data)
                    system.result_queue.put(result)
                elif cmd == 'connected':
                    system.on_connected(data)
            
            except queue.Empty:
                pass
            
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\n退出...")


if __name__ == "__main__":
    main()

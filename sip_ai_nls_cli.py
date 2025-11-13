#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI对话系统 - 阿里云NLS WebSocket CLI版本
纯命令行版本，无Web界面

使用方法:
    python3 sip_ai_nls_cli.py 85211111111
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
    'ai_model': 'gpt-4.1-nano',
    
    # WebRTC VAD配置 - 优化版
    'vad_aggressiveness': 1,       # 宽容模式（更少误判）
    'vad_frame_duration': 30,      # 30ms帧
    'vad_silence_frames': 15,      # 450ms静音即结束（原20=600ms）
    'vad_min_speech_frames': 3,    # 90ms即触发（原5=150ms）
    'vad_max_speech_frames': 100,  # 最多3秒音频（新增！防止太长）
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
                    
                    # 达到最大长度，强制结束（防止音频太长）
                    if len(self.speech_frames) >= self.max_speech_frames:
                        print(f"  [VAD] 达到最大长度，强制结束 ({len(self.speech_frames)}帧 = {len(self.speech_frames)*0.03:.1f}秒)")
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


# ==================== 阿里云NLS ASR引擎 ====================

class NLSASREngine:
    """阿里云NLS实时语音识别引擎"""
    
    def __init__(self):
        self.token = None
        self.appkey = CONFIG['nls_appkey']
        self.token_lock = threading.Lock()
        # 预先获取token
        print("  [ASR] 预获取Token...")
        self.get_token()
    
    def get_token(self):
        """获取访问token"""
        with self.token_lock:
            if not self.token:
                try:
                    self.token = getToken(CONFIG['nls_akid'], CONFIG['nls_akkey'])
                    print(f"  [ASR] Token OK: {self.token[:20]}...")
                except Exception as e:
                    print(f"  [ASR] Token获取失败: {e}")
                    return False
        return True
    
    def transcribe(self, audio_file):
        """识别音频文件"""
        if not self.get_token():
            return ""
        
        try:
            total_start = time.time()
            
            with open(audio_file, 'rb') as f:
                audio_data = f.read()
            
            print(f"  [ASR] 音频大小: {len(audio_data)} 字节")
            
            result_container = {'text': '', 'completed': False, 'error': None}
            lock = threading.Lock()
            condition = threading.Condition(lock)
            
            def on_start(message, *args):
                print(f"  [ASR] 识别器已启动")
            
            def on_completed(message, *args):
                with condition:
                    try:
                        print(f"  [ASR] 收到完成回调")
                        msg = json.loads(message)
                        if 'payload' in msg and 'result' in msg['payload']:
                            result_container['text'] = msg['payload']['result']
                        else:
                            print(f"  [ASR] 警告: 结果为空 - {message}")
                    except Exception as e:
                        print(f"  [ASR] 解析错误: {e}")
                    result_container['completed'] = True
                    condition.notify()
            
            def on_error(message, *args):
                with condition:
                    print(f"  [ASR] 错误回调: {message}")
                    result_container['error'] = message
                    result_container['completed'] = True
                    condition.notify()
            
            def on_close(*args):
                with condition:
                    print(f"  [ASR] 连接关闭")
                    if not result_container['completed']:
                        result_container['completed'] = True
                        condition.notify()
            
            sr = nls.NlsSpeechRecognizer(
                token=self.token,
                appkey=self.appkey,
                on_start=on_start,
                on_completed=on_completed,
                on_error=on_error,
                on_close=on_close
            )
            
            send_start = time.time()
            
            sr.start(
                aformat="pcm",
                sample_rate=8000,
                enable_intermediate_result=False,
                enable_punctuation_prediction=False,  # 禁用标点，加快速度
                enable_inverse_text_normalization=False  # 禁用反标准化，加快速度
            )
            
            # 快速发送音频数据 - 不要延迟，直接发送
            chunk_size = 6400  # 400ms chunks，更快
            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i:i+chunk_size]
                sr.send_audio(chunk)
                # 不sleep，直接发送
            
            sr.stop()
            
            send_elapsed = time.time() - send_start
            print(f"  [ASR] 发送耗时: {send_elapsed:.1f}s")
            
            wait_start = time.time()
            
            # 增加超时时间
            with condition:
                condition.wait(timeout=30)
            
            wait_elapsed = time.time() - wait_start
            print(f"  [ASR] 等待耗时: {wait_elapsed:.1f}s")
            
            elapsed = time.time() - total_start
            text = result_container.get('text', '').strip()
            
            if text:
                print(f"  [ASR] 识别: '{text}' ({elapsed:.1f}s)")
            
            return text
            
        except Exception as e:
            print(f"  [ASR] 识别失败: {e}")
            return ""


# ==================== 阿里云NLS TTS引擎 ====================

class NLSTTSEngine:
    """阿里云NLS语音合成引擎"""
    
    def __init__(self):
        self.token = None
        self.appkey = CONFIG['nls_appkey']
        self.voice = CONFIG['nls_tts_voice']
        self.token_lock = threading.Lock()
        # 预先获取token
        print("  [TTS] 预获取Token...")
        self.get_token()
    
    def get_token(self):
        """获取访问token"""
        with self.token_lock:
            if not self.token:
                try:
                    self.token = getToken(CONFIG['nls_akid'], CONFIG['nls_akkey'])
                    print(f"  [TTS] Token OK: {self.token[:20]}...")
                except Exception as e:
                    print(f"  [TTS] Token获取失败: {e}")
                    return False
        return True
    
    def synthesize(self, text):
        """合成语音"""
        if not text or not text.strip():
            return None
        
        if not self.get_token():
            return None
        
        try:
            start_time = time.time()
            
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            output_file = os.path.join(CONFIG['temp_dir'], f"tts_nls_{ts}.wav")
            
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
                    pass
            
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
            
            tts = nls.NlsSpeechSynthesizer(
                token=self.token,
                appkey=self.appkey,
                on_data=on_data,
                on_completed=on_completed,
                on_error=on_error,
                on_close=on_close
            )
            
            tts.start(
                text=text,
                voice=self.voice,
                aformat="wav",
                sample_rate=8000,
                volume=50,
                speech_rate=0
            )
            
            with condition:
                condition.wait(timeout=30)
            
            elapsed = time.time() - start_time
            
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                size = os.path.getsize(output_file)
                print(f"  [TTS] 合成完成 ({size}字节, {elapsed:.1f}s)")
                return output_file
            else:
                return None
            
        except Exception as e:
            print(f"  [TTS] 合成失败: {e}")
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
            return "Maaf, saya tidak dapat menjawab sekarang."
        
        try:
            start_time = time.time()
            
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
            elapsed = time.time() - start_time
            
            self.conversation_history.append({"role": "user", "content": user_input})
            self.conversation_history.append({"role": "assistant", "content": ai_response})
            
            print(f"  [AI]  回复: '{ai_response}' ({elapsed:.1f}s)")
            return ai_response
            
        except Exception as e:
            print(f"  [AI]  错误: {e}")
            return "Maaf, terjadi kesalahan."


# ==================== 实时录音文件读取器 ====================

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
        except Exception as e:
            pass
        return b''


# ==================== AI对话回调 ====================

class AIConversationCallback(pj.CallCallback):
    """AI对话呼叫回调"""
    
    def __init__(self, call=None):
        pj.CallCallback.__init__(self, call)
        self.connected = False
        self.lock = threading.Lock()
        
        self.vad = WebRTCVADDetector(CONFIG['vad_aggressiveness'], CONFIG['vad_frame_duration'])
        self.wav_reader = None
        self.vad_thread = None
        self.vad_running = False
        
        self.asr = NLSASREngine()
        self.tts = NLSTTSEngine()
        self.dialogue = DialogueEngine()
        
        self.recorder = None
        self.recorder_id = None
        self.record_file = None
    
    def on_state(self):
        """呼叫状态变化"""
        try:
            info = self.call.info()
            print(f"\n[状态] {info.state_text} - {info.last_code}")
            
            if info.state == pj.CallState.CONFIRMED:
                with self.lock:
                    self.connected = True
                print("[状态] >>> 通话已接通，AI对话系统已激活\n")
                self.start_vad_recording()
                
            elif info.state == pj.CallState.DISCONNECTED:
                with self.lock:
                    self.connected = False
                print("\n[状态] >>> 通话已结束")
                self.stop_vad_recording()
        except Exception as e:
            print(f"[错误] {e}")
    
    def on_media_state(self):
        """媒体状态变化"""
        try:
            info = self.call.info()
            if info.media_state == pj.MediaState.ACTIVE:
                call_slot = info.conf_slot
                pj.Lib.instance().conf_connect(call_slot, 0)
                pj.Lib.instance().conf_connect(0, call_slot)
        except Exception as e:
            pass
    
    def start_vad_recording(self):
        """开始VAD录音"""
        try:
            info = self.call.info()
            
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.record_file = os.path.join(CONFIG['recordings_dir'], f"call_nls_{ts}.wav")
            
            self.recorder = pj.Lib.instance().create_recorder(self.record_file)
            self.recorder_id = pj.Lib.instance().recorder_get_slot(self.recorder)
            
            call_slot = info.conf_slot
            pj.Lib.instance().conf_connect(call_slot, self.recorder_id)
            
            print(f"[录音] {self.record_file}")
            
            self.wav_reader = RealtimeWavReader(self.record_file)
            
            self.vad_running = True
            self.vad_thread = threading.Thread(target=self.vad_process_loop, daemon=True)
            self.vad_thread.start()
            
        except Exception as e:
            print(f"[错误] 启动录音失败: {e}")
    
    def stop_vad_recording(self):
        """停止VAD录音"""
        try:
            self.vad_running = False
            if self.vad_thread:
                self.vad_thread.join(timeout=2)
            
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
            
            print(f"[录音] 已保存: {self.record_file}")
            
        except Exception as e:
            pass
    
    def vad_process_loop(self):
        """VAD处理循环"""
        last_read_time = time.time()
        read_interval = 0.1
        
        while self.vad_running:
            try:
                current_time = time.time()
                
                if current_time - last_read_time >= read_interval:
                    new_data = self.wav_reader.read_new_data()
                    last_read_time = current_time
                    
                    if new_data:
                        if self.wav_reader.last_pos <= 44:
                            continue
                        
                        result = self.vad.process_audio(new_data)
                        
                        if result and result[0] == 'speech_complete':
                            audio_data = result[1]
                            self.process_speech(audio_data)
                
                time.sleep(0.05)
                
            except Exception as e:
                time.sleep(0.5)
    
    def process_speech(self, audio_data):
        """处理语音 - 在独立线程中处理，避免阻塞"""
        # 使用独立线程处理，避免PJSIP线程问题
        thread = threading.Thread(target=self._process_speech_thread, args=(audio_data,), daemon=True)
        thread.start()
    
    def _process_speech_thread(self, audio_data):
        """处理语音的线程函数"""
        try:
            print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            speech_file = os.path.join(CONFIG['temp_dir'], f"speech_{ts}.wav")
            
            with wave.open(speech_file, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(8000)
                wf.writeframes(audio_data)
            
            text = self.asr.transcribe(speech_file)
            
            if text:
                response = self.dialogue.get_response(text)
                
                if response:
                    tts_file = self.tts.synthesize(response)
                    
                    if tts_file:
                        self.play_audio_response(tts_file)
            
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
            
        except Exception as e:
            print(f"[错误] {e}\n")
    
    def play_audio_response(self, audio_file):
        """播放AI回复"""
        try:
            print(f"  [播放] 正在播放AI回复...")
            
            player = pj.Lib.instance().create_player(audio_file, loop=False)
            player_slot = pj.Lib.instance().player_get_slot(player)
            
            info = self.call.info()
            pj.Lib.instance().conf_connect(player_slot, info.conf_slot)
            
            while pj.Lib.instance().player_get_pos(player) >= 0:
                time.sleep(0.1)
                if not self.connected:
                    break
            
            pj.Lib.instance().conf_disconnect(player_slot, info.conf_slot)
            pj.Lib.instance().player_destroy(player)
            
            print(f"  [播放] 完成")
            
        except Exception as e:
            print(f"[错误] 播放失败: {e}")


# ==================== 主程序 ====================

def main():
    if len(sys.argv) < 2:
        print("=" * 70)
        print("  AI对话系统 - 阿里云NLS CLI版")
        print("=" * 70)
        print("\n使用方法:")
        print("  python3 sip_ai_nls_cli.py <电话号码>")
        print("\n示例:")
        print("  python3 sip_ai_nls_cli.py 85211111111")
        print("\n说明:")
        print("  • 会自动加前缀 13462")
        print("  • 按 Ctrl+C 挂断电话")
        print("  • 录音保存在 recordings/ 目录")
        print()
        return
    
    phone_number = sys.argv[1].strip()
    
    print("=" * 70)
    print("  AI对话系统 - 阿里云NLS CLI版")
    print("=" * 70)
    print(f"  ASR: 阿里云NLS WebSocket")
    print(f"  TTS: 阿里云NLS WebSocket (发音人: {CONFIG['nls_tts_voice']})")
    print(f"  AI:  OpenAI {CONFIG['ai_model']}")
    print(f"  VAD: WebRTC (激进度: {CONFIG['vad_aggressiveness']})")
    print("=" * 70)
    
    if not CONFIG['openai_api_key']:
        print("\n⚠ 错误: 未设置 OPENAI_API_KEY")
        print("  请运行: export OPENAI_API_KEY='your-key'")
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
        print(f"[SIP] 服务器: {CONFIG['server']}:{CONFIG['port']}")
        
        # 拨号
        full_number = f"{CONFIG['prefix']}{phone_number}"
        uri = f"sip:{full_number}@{CONFIG['server']}"
        
        print(f"\n[拨号] {uri}")
        print("[提示] 按 Ctrl+C 挂断\n")
        
        call = acc.make_call(uri)
        call.set_callback(AIConversationCallback(call))
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n[挂断] 正在挂断电话...")
            if call.is_valid():
                call.hangup()
            time.sleep(2)
        
        lib.destroy()
        lib = None
        
        print("[退出] 再见！\n")
    
    except pj.Error as e:
        print(f"\n[错误] PJSUA: {e}")
        if lib:
            lib.destroy()
    except Exception as e:
        print(f"\n[错误] {e}")
        if lib:
            lib.destroy()


if __name__ == "__main__":
    main()

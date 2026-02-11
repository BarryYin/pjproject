#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sip_ai_streaming_id_test.py - 印尼语场景，公网服务器版（无 NAT/STUN）

与 sip_ai_streaming_bargein_id.py 功能相同，但 不做 STUN/NAT 穿透。
用于部署在 具有公网 IP 的服务器 上测试印尼线路拨通。

为何公网服务器不需要 NAT 穿透：
- 机器本身有公网 IP 时，Via/Contact/SDP 会直接使用该公网地址；
- 147.139.205.88 回 100/180/200 到该公网 IP 即可送达，无 NAT 阻隔。
- 仅当运行在 NAT 后（如本机/家庭网络）才需要 STUN。
"""

import pjsua2 as pj
import sys
import os
import time
import threading
import wave
import json
import queue
import atexit
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

SCRIPT_DIR = Path(__file__).parent
LOGS_DIR = SCRIPT_DIR / "logs"
os.makedirs(LOGS_DIR, exist_ok=True)

# 运行日志：同时输出到控制台和 logs/*.log
_log_file = None
_original_stdout = None
_original_stderr = None

class _Tee:
    """将写入同时发往原流和日志文件"""
    def __init__(self, stream, file_handle):
        self._stream = stream
        self._file = file_handle
    def write(self, data):
        if data:
            try:
                self._stream.write(data)
                self._stream.flush()
            except Exception:
                pass
            try:
                self._file.write(data)
                self._file.flush()
            except Exception:
                pass
    def flush(self):
        try:
            self._stream.flush()
            self._file.flush()
        except Exception:
            pass
    def isatty(self):
        return getattr(self._stream, "isatty", lambda: False)()

def _init_run_log():
    """按日期写入 logs/ 下当日 .log 文件（追加），并 tee stdout/stderr 到该文件。"""
    global _log_file, _original_stdout, _original_stderr
    if _log_file is not None:
        return
    date_str = datetime.now().strftime("%Y%m%d")
    log_path = LOGS_DIR / f"sip_ai_streaming_id_test_{date_str}.log"
    _log_file = open(log_path, "a", encoding="utf-8")
    run_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _log_file.write(f"\n{'='*60}\n>>> {run_ts} 新运行\n{'='*60}\n")
    _log_file.flush()
    _original_stdout = sys.stdout
    _original_stderr = sys.stderr
    sys.stdout = _Tee(_original_stdout, _log_file)
    sys.stderr = _Tee(_original_stderr, _log_file)
    atexit.register(_close_run_log)
    print(f"[日志] 运行日志追加写入: {log_path}")

def _close_run_log():
    """退出时恢复 stdout/stderr 并关闭日志文件。"""
    global _log_file, _original_stdout, _original_stderr
    if _log_file is None:
        return
    try:
        sys.stdout = _original_stdout
        sys.stderr = _original_stderr
        _log_file.close()
    except Exception:
        pass
    _log_file = None
    _original_stdout = None
    _original_stderr = None

def _trace(stage, event, detail=None, error=None, duration=None):
    """服务链路追踪：ASR / LLM / TTS / PIPELINE，同步写入当日运行 log。"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    parts = [f"[追踪] {ts} | {stage} | {event}"]
    if detail is not None:
        parts.append(f" | {detail}")
    if error is not None:
        parts.append(f" | 错误: {error}")
    if duration is not None:
        parts.append(f" | 耗时: {duration:.2f}s")
    line = "".join(parts) + "\n"
    try:
        print(line.rstrip())
    except Exception:
        pass

CONFIG = {
    'sip_server': os.getenv('SIP_SERVER', '147.139.205.88'),
    'sip_port': int(os.getenv('SIP_PORT', '5060')),
    'sip_tcp_port': int(os.getenv('SIP_TCP_PORT') or os.getenv('SIP_PORT', '5060')),
    'sip_transport': os.getenv('SIP_TRANSPORT', 'udp').lower(),
    'sip_user': os.getenv('SIP_CALLER_NUMBER', '6281479242434'),
    'sip_password': os.getenv('SIP_PASSWORD', ''),
    'sip_prefix': os.getenv('SIP_PREFIX', '13462').strip(),
    'temp_dir': str(SCRIPT_DIR / 'temp_audio'),
    'openai_api_key': os.getenv('OPENAI_API_KEY', ''),
    'ai_model': os.getenv('AI_MODEL', 'gpt-4o-mini'),
    'scenario': os.getenv('SCENARIO', 'collection'),
    'customer_name': os.getenv('CUSTOMER_NAME', 'Ahmad'),
    'customer_gender': os.getenv('CUSTOMER_GENDER', 'Bapak'),
    'collect_amount': os.getenv('COLLECT_AMOUNT', '500000'),
    'total_collect_amount': os.getenv('TOTAL_COLLECT_AMOUNT', '1000000'),
    'due_date': os.getenv('DUE_DATE', '2026-02-10'),
    'due_scenarios': os.getenv('DUE_SCENARIOS', 'D1'),
    'sample_rate': 16000,
    'frame_duration': 20,
    'playback_gain': float(os.getenv('PLAYBACK_GAIN', '2.0')),
    'max_call_duration_sec': int(os.getenv('MAX_CALL_DURATION_SEC', '120')),
    'goodbye_keywords': [
        'dada', 'dada ', 'dah ya', 'sampai jumpa', 'terima kasih', 'selamat tinggal',
        'tidak perlu', 'saya tutup', 'sudah', 'cukup', 'sudah cukup',
        'bye bye', 'bye', 'goodbye', 'good bye', 'see you',
    ],
    'non_interrupt_words': [
        'ya', 'yah', 'iya', 'ok', 'oke', 'baik', 'sip', 'oh', 'oo',
        'yes', 'yeah', 'yep', 'okay', 'tidak', 'no', 'nope',
        'hm', 'hmm', 'mm', 'mmm', 'uh', 'um', 'ah', 'eh',
    ],
    'farewell_message': 'Baik, terima kasih. Sampai jumpa.',
    'recording_dir': str(SCRIPT_DIR / 'logs' / 'recordings'),
    'recording_enabled': os.getenv('RECORDING_ENABLED', 'true').lower() in ('1', 'true', 'yes'),
}

os.makedirs(CONFIG['temp_dir'], exist_ok=True)
if CONFIG.get('recording_enabled'):
    os.makedirs(CONFIG['recording_dir'], exist_ok=True)


def apply_wav_gain(wav_path, gain):
    if gain is None or abs(gain - 1.0) < 0.01:
        return
    try:
        with wave.open(wav_path, 'rb') as wf:
            nch, sampw, sr, nf, _, _ = wf.getparams()
            if sampw != 2:
                return
            frames = wf.readframes(nf)
        import struct
        fmt = '<%dh' % (len(frames) // 2)
        samples = list(struct.unpack(fmt, frames))
        out = [max(-32767, min(32767, int(round(s * gain)))) for s in samples]
        with wave.open(wav_path, 'wb') as wf:
            wf.setnchannels(nch)
            wf.setsampwidth(sampw)
            wf.setframerate(sr)
            wf.writeframes(struct.pack(fmt, *out))
    except Exception as e:
        print(f"  [增益] 跳过: {e}")


def _mix_recordings_to_wav(remote_wav_path, local_segments, recording_start_time, out_path, sample_rate=8000):
    """将对方轨与己方轨按时间对齐混成单轨 WAV。"""
    import struct
    try:
        file_size = os.path.getsize(remote_wav_path) if os.path.exists(remote_wav_path) else 0
        if file_size < 8:
            print(f"  [录音] 远程录音文件过小或为空 ({file_size} bytes): {remote_wav_path}")
            return False
        remote_pcm = None
        r_sr = 8000
        try:
            with wave.open(remote_wav_path, 'rb') as wf:
                r_nch, r_sw, r_sr, r_nf, _, _ = wf.getparams()
                remote_pcm = wf.readframes(r_nf)
            if r_sw != 2:
                print(f"  [录音] 远程 WAV 非 16bit (sw={r_sw})，尝试 raw PCM 回退")
                remote_pcm = None
        except Exception as wav_err:
            print(f"  [录音] 远程文件非标准 WAV ({wav_err})，尝试 raw PCM 回退")
            remote_pcm = None
        if remote_pcm is None:
            with open(remote_wav_path, 'rb') as f:
                raw_data = f.read()
            if len(raw_data) > 44 and raw_data[:4] == b'RIFF':
                remote_pcm = raw_data[44:]
            else:
                remote_pcm = raw_data
            # 采样率使用会议桥时钟（通常 16kHz），而非 8kHz，否则音频会被拉长到两倍时长
            r_sr = CONFIG.get('sample_rate', 16000)
            print(f"  [录音] 以 raw PCM 读取远程音频 ({len(remote_pcm)} bytes, 假设 {r_sr}Hz)")
        if len(remote_pcm) < 2:
            print(f"  [录音] 远程音频数据为空")
            return False
        fmt = '<%dh' % (len(remote_pcm) // 2)
        remote_samples = list(struct.unpack(fmt, remote_pcm[:len(remote_pcm) // 2 * 2]))
        print(f"  [录音] 远程轨: {len(remote_samples)} samples ({len(remote_samples)/r_sr:.1f}s @ {r_sr}Hz)")
        if r_sr != sample_rate and r_sr > 0:
            ratio = sample_rate / r_sr
            remote_samples = [remote_samples[min(int(i / ratio), len(remote_samples) - 1)] for i in range(int(len(remote_samples) * ratio))]
        total_len = len(remote_samples)
        local_samples = [0] * total_len
        local_seg_count = 0
        for start_sec, pcm_bytes, sr in (local_segments or []):
            if not pcm_bytes or len(pcm_bytes) < 2:
                continue
            local_seg_count += 1
            n = len(pcm_bytes) // 2
            seg = list(struct.unpack('<%dh' % n, pcm_bytes[: n * 2]))
            if sr == 16000 and sample_rate == 8000:
                seg = [seg[i * 2] for i in range(len(seg) // 2)]
            start_idx = int(start_sec * sample_rate)
            for i, s in enumerate(seg):
                idx = start_idx + i
                if idx >= total_len:
                    total_len = idx + 1
                    local_samples.extend([0] * (total_len - len(local_samples)))
                if idx < len(local_samples):
                    local_samples[idx] = s
        print(f"  [录音] 本地轨: {local_seg_count} 段 TTS 音频")
        if total_len > len(remote_samples):
            remote_samples.extend([0] * (total_len - len(remote_samples)))
        if total_len > len(local_samples):
            local_samples.extend([0] * (total_len - len(local_samples)))
        # 远端电话音频通常比本地 TTS 弱很多，需要先做增益再混合
        remote_gain = float(CONFIG.get('playback_gain', 3.0))
        mixed = []
        for i in range(total_len):
            r = remote_samples[i] if i < len(remote_samples) else 0
            l = local_samples[i] if i < len(local_samples) else 0
            v = int(r * remote_gain * 0.5 + l * 0.5)
            mixed.append(max(-32767, min(32767, v)))
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with wave.open(out_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(struct.pack('<%dh' % len(mixed), *mixed))
        duration = len(mixed) / sample_rate
        print(f"  [录音] 混轨完成: {duration:.1f}s, {os.path.getsize(out_path)} bytes")
        return True
    except Exception as e:
        import traceback
        print(f"  [录音] 混轨失败: {e}")
        traceback.print_exc()
        return False


# ==================== 流式 ASR ====================
class StreamingASR:
    def __init__(self, on_sentence_end):
        self.on_sentence_end = on_sentence_end
        self.recognition = None
        self.connected = False
        self.current_text = ""
        import dashscope
        self.api_key = os.getenv('DASHSCOPE_API_KEY', '')
        dashscope.api_key = self.api_key

    def start(self):
        try:
            from dashscope.audio.asr import Recognition, RecognitionCallback, RecognitionResult
            asr_instance = self
            class ASRCallback(RecognitionCallback):
                def on_open(self) -> None:
                    asr_instance.connected = True
                    print("[ASR] ✓ 已连接")
                def on_complete(self) -> None:
                    print("[ASR] 识别完成")
                def on_error(self, result: RecognitionResult) -> None:
                    print(f"[ASR] 错误: {result.message}")
                def on_event(self, result: RecognitionResult) -> None:
                    sentence = result.get_sentence()
                    if sentence:
                        text = sentence.get("text", "")
                        is_end = RecognitionResult.is_sentence_end(sentence)
                        if text:
                            asr_instance.current_text = text
                            if is_end:
                                print(f"\n  [ASR] ✓ 识别完成: {text}")
                                _trace("ASR", "result", detail=f'识别: "{text[:80]}{"..." if len(text) > 80 else ""}"')
                                if asr_instance.on_sentence_end and text.strip():
                                    asr_instance.on_sentence_end(text.strip())
                                asr_instance.current_text = ""
                            else:
                                print(f"  [ASR] 识别中: {text}", end='\r')
                def on_close(self) -> None:
                    asr_instance.connected = False
                    print("[ASR] 已关闭")
            self.recognition = Recognition(
                model='paraformer-realtime-v2',
                format='pcm',
                sample_rate=CONFIG['sample_rate'],
                language_hints=['en'],
                callback=ASRCallback()
            )
            self.recognition.start()
            for _ in range(30):
                if self.connected:
                    break
                time.sleep(0.1)
            if self.connected:
                print("[ASR] ✓ DashScope 流式 ASR 已启动 (印尼语)")
                _trace("ASR", "start", detail="DashScope paraformer-realtime-v2 已连接")
                return True
            print("[ASR] ✗ 连接超时")
            _trace("ASR", "fail", error="连接超时")
            return False
        except Exception as e:
            print(f"[ASR] ✗ 启动失败: {e}")
            _trace("ASR", "fail", error=str(e))
            import traceback
            traceback.print_exc()
            return False

    def feed_audio(self, pcm_data):
        if self.connected and self.recognition:
            try:
                self.recognition.send_audio_frame(pcm_data)
            except Exception as e:
                print(f"[ASR] 发送音频失败: {e}")
                _trace("ASR", "fail", error=str(e))

    def stop(self):
        if self.recognition:
            try:
                self.recognition.stop()
            except:
                pass
        self.connected = False


# ==================== TTS ====================
class TTSEngine:
    def __init__(self):
        try:
            import dashscope
            from dashscope.audio.tts import SpeechSynthesizer
            self.dashscope = dashscope
            self.SpeechSynthesizer = SpeechSynthesizer
            self.dashscope.api_key = os.getenv('DASHSCOPE_API_KEY', '')
            self.model = os.getenv('TTS_VOICE', 'sambert-indah-v1')
            self.initialized = True
            print(f"[TTS] ✓ DashScope TTS 已初始化 (voice: {self.model})")
        except Exception as e:
            print(f"[TTS] ✗ 初始化失败: {e}")
            _trace("TTS", "fail", error=f"初始化: {e}")
            self.initialized = False

    def synthesize(self, text):
        if not self.initialized:
            _trace("TTS", "skip", detail="未初始化")
            return None
        try:
            start = time.time()
            _trace("TTS", "request", detail=f'合成: "{text[:80]}{"..." if len(text) > 80 else ""}"')
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            wav = os.path.join(CONFIG['temp_dir'], f"tts_{ts}.wav")
            result = self.SpeechSynthesizer.call(
                model=self.model, text=text, sample_rate=16000, format='wav'
            )
            if result.get_audio_data() is None:
                raise Exception("未生成音频数据")
            with open(wav, 'wb') as f:
                f.write(result.get_audio_data())
            elapsed = time.time() - start
            print(f"  [TTS] 完成 ({elapsed:.1f}s)")
            _trace("TTS", "done", duration=elapsed)
            return wav
        except Exception as e:
            print(f"  [TTS] 失败: {e}")
            _trace("TTS", "fail", error=str(e))
            return None


# ==================== AI ====================
class AIEngine:
    def __init__(self):
        self.context = []
        self._load_prompt()
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=CONFIG['openai_api_key'])
            print(f"[AI] ✓ GPT 已初始化 (model: {CONFIG['ai_model']})")
        except Exception as e:
            print(f"[AI] ✗ 初始化失败: {e}")
            _trace("LLM", "fail", error=f"初始化: {e}")
            self.client = None

    def _load_prompt(self):
        try:
            from config.prompts import get_filled_prompt, get_filled_introduction
            variables = {
                'Name': CONFIG.get('customer_name', 'Ahmad'),
                'Gender': CONFIG.get('customer_gender', 'Bapak'),
                'CollectAmount': CONFIG.get('collect_amount', '500000'),
                'TotalCollectAmount': CONFIG.get('total_collect_amount', '1000000'),
                'Due_date': CONFIG.get('due_date', '2026-02-10'),
                'Due_scenarios': CONFIG.get('due_scenarios', 'D1'),
                'scenario': CONFIG.get('scenario', 'collection'),
            }
            self.system_prompt = get_filled_prompt(variables)
            self.introduction = get_filled_introduction(variables)
            print(f"  开场白: {self.introduction[:40]}...")
        except Exception as e:
            print(f"  [Prompt] 加载失败: {e}，使用默认印尼语")
            self.system_prompt = "Anda asisten virtual. Jawab singkat dalam Bahasa Indonesia."
            self.introduction = "Halo, ada yang bisa saya bantu?"

    def get_introduction(self):
        return self.introduction

    def get_response(self, user_text):
        if not self.client or not user_text:
            _trace("LLM", "skip", detail="client或输入为空")
            return None
        try:
            _trace("LLM", "request", detail=f'输入: "{user_text[:80]}{"..." if len(user_text) > 80 else ""}"')
            self.context.append({"role": "user", "content": user_text})
            response = self.client.chat.completions.create(
                model=CONFIG['ai_model'],
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    *self.context[-20:]
                ],
                max_tokens=100,
                temperature=0.7
            )
            reply = response.choices[0].message.content.strip()
            self.context.append({"role": "assistant", "content": reply})
            _trace("LLM", "response", detail=f'输出: "{reply[:80]}{"..." if len(reply) > 80 else ""}"')
            return reply
        except Exception as e:
            print(f"[AI] 错误: {e}")
            _trace("LLM", "fail", error=str(e))
            return None


# ==================== 音频端口 ====================
class StreamingAudioPort(pj.AudioMediaPort):
    def __init__(self, callback):
        pj.AudioMediaPort.__init__(self)
        self.callback = callback
        self.frame_count = 0
        self.is_playing = True
        fmt = pj.MediaFormatAudio()
        fmt.init(
            pj.PJMEDIA_FORMAT_L16,
            CONFIG['sample_rate'], 1,
            CONFIG['frame_duration'] * 1000, 16,
            CONFIG['sample_rate'] * 2
        )
        self.createPort("streaming_port", fmt)
        print(f"[音频端口] 已创建 ({CONFIG['sample_rate']}Hz)")

    def onFrameReceived(self, frame):
        self.frame_count += 1
        if self.frame_count % 250 == 0:
            print(f"  [音频] 已接收 {self.frame_count} 帧 (playing={self.is_playing})")
        if self.callback.streaming_asr and self.callback.streaming_asr.connected:
            self.callback.streaming_asr.feed_audio(bytes(frame.buf))


# ==================== 呼叫回调 ====================
class CallCallback(pj.Call):
    def __init__(self, acc, call_id=pj.PJSUA_INVALID_ID, hangup_callback=None, clear_on_disconnect_callback=None):
        pj.Call.__init__(self, acc, call_id)
        self.acc = acc
        self.hangup_callback = hangup_callback
        self.clear_on_disconnect_callback = clear_on_disconnect_callback
        self.connected = False
        self.audio_port = None
        self.audio_setup_done = False
        self.is_processing = False
        self.processing_lock = threading.Lock()
        self.call_start_time = None
        self._stop_playback = False
        self._playback_lock = threading.Lock()
        self._is_ending = False
        self.tts = TTSEngine()
        self.ai = AIEngine()
        self.streaming_asr = None
        # 通话录音（双方混轨为单文件）
        self._recorder_remote = None
        self._aud_med_for_recording = None
        self.recording_start_time = None
        self._local_recording = []
        self._recording_remote_path = None
        self._recording_ts = None
        # 防重复：避免 ASR 误识别同一句导致 AI 反复说同一句话
        self._last_user_speech_text = None
        self._last_user_speech_time = 0.0

    def onCallState(self, prm):
        ci = self.getInfo()
        state_name = {
            pj.PJSIP_INV_STATE_NULL: "NULL",
            pj.PJSIP_INV_STATE_CALLING: "CALLING",
            pj.PJSIP_INV_STATE_INCOMING: "INCOMING",
            pj.PJSIP_INV_STATE_EARLY: "EARLY",
            pj.PJSIP_INV_STATE_CONNECTING: "CONNECTING",
            pj.PJSIP_INV_STATE_CONFIRMED: "CONFIRMED",
            pj.PJSIP_INV_STATE_DISCONNECTED: "DISCONNECTED",
        }.get(ci.state, str(ci.state))
        print(f"\n[呼叫] {state_name}")
        if ci.state == pj.PJSIP_INV_STATE_EARLY:
            # 振铃/早期媒体，不播欢迎语，等 CONFIRMED 再建媒体
            print("  振铃中，等待对方接听...")
        elif ci.state == pj.PJSIP_INV_STATE_CONFIRMED:
            self.connected = True
            self.call_start_time = time.time()
            print("  ✓ 通话已接通")
            # 媒体可能在 EARLY 时已 ACTIVE，进入 CONFIRMED 后 onCallMediaState 可能不再触发，此处主动启动 setup_audio
            if not self.audio_setup_done:
                self.audio_setup_done = True
                threading.Thread(target=self.setup_audio, daemon=True).start()
            if self.hangup_callback:
                def _duration_check():
                    try:
                        pj.Endpoint.instance().libRegisterThread("duration_check")
                    except Exception:
                        pass
                    while self.connected and self.call_start_time:
                        time.sleep(15)
                        if not self.connected:
                            break
                        if time.time() - self.call_start_time >= CONFIG['max_call_duration_sec']:
                            print(f"\n  [挂断] 通话时长已达 {CONFIG['max_call_duration_sec']}s")
                            self.hangup_callback()
                            break
                threading.Thread(target=_duration_check, daemon=True).start()
        elif ci.state == pj.PJSIP_INV_STATE_DISCONNECTED:
            self.connected = False
            if self.streaming_asr:
                self.streaming_asr.stop()
            print("  通话已结束")
            # 挂断原因（与 sip_test_call_indonesia 一致）
            try:
                code = getattr(ci, 'lastStatusCode', 0) or 0
                reason = getattr(ci, 'lastReason', '') or ''
                if code == 200:
                    print("  原因: 正常挂断")
                elif code == 486:
                    print("  原因: 用户忙")
                elif code == 487:
                    print("  原因: 请求已取消")
                elif code == 480:
                    print("  原因: 暂时无法接通")
                elif code == 404:
                    print("  原因: 号码不存在")
                elif code == 403:
                    print("  原因: 禁止呼叫")
                elif code == 408:
                    print("  原因: 请求超时")
                elif code == 603:
                    print("  原因: 拒绝接听")
                else:
                    print(f"  原因: {reason}" if reason else f"  原因: 代码 {code}")
            except Exception:
                pass
            # 录音混轨并保存（若已开启），再清空 current_call
            if self.clear_on_disconnect_callback:
                def _finish_recording_and_clear():
                    try:
                        pj.Endpoint.instance().libRegisterThread("disconnected_clear")
                    except Exception:
                        pass
                    rec_remote = getattr(self, '_recording_remote_path', None)
                    rec_enabled = CONFIG.get('recording_enabled')
                    if rec_enabled and rec_remote and os.path.exists(rec_remote):
                        try:
                            try:
                                aud = getattr(self, '_aud_med_for_recording', None)
                                rec = getattr(self, '_recorder_remote', None)
                                if aud and rec:
                                    aud.stopTransmit(rec)
                            except Exception:
                                pass
                            try:
                                if self._recorder_remote is not None:
                                    self._recorder_remote = None
                            except Exception:
                                pass
                            time.sleep(0.5)
                            local_segments = getattr(self, '_local_recording', []) or []
                            rec_dir = CONFIG.get('recording_dir') or str(SCRIPT_DIR / 'logs' / 'recordings')
                            ts = getattr(self, '_recording_ts', None) or datetime.now().strftime("%Y%m%d_%H%M%S")
                            final_path = os.path.join(rec_dir, f"call_{ts}_mixed.wav")
                            rec_start = getattr(self, 'recording_start_time', 0) or 0
                            ok = _mix_recordings_to_wav(rec_remote, local_segments, rec_start, final_path)
                            if ok:
                                print(f"  [录音] ✓ 已保存: {final_path}")
                            else:
                                print(f"  [录音] 混轨返回失败，远程文件: {rec_remote} (大小: {os.path.getsize(rec_remote) if os.path.exists(rec_remote) else 'N/A'} bytes)")
                            try:
                                if os.path.exists(rec_remote):
                                    os.remove(rec_remote)
                            except Exception:
                                pass
                        except Exception as e:
                            import traceback
                            print(f"  [录音] 混轨/保存失败: {e}")
                            traceback.print_exc()
                    self.clear_on_disconnect_callback()
                threading.Thread(target=_finish_recording_and_clear, daemon=True).start()

    def onCallMediaState(self, prm):
        ci = self.getInfo()
        for i, mi in enumerate(ci.media):
            if mi.type == pj.PJMEDIA_TYPE_AUDIO and mi.status == pj.PJSUA_CALL_MEDIA_ACTIVE:
                # 仅在接通(CONFIRMED)时建媒体并播欢迎语；振铃(EARLY)时只提示，不建媒体
                if ci.state == pj.PJSIP_INV_STATE_EARLY:
                    print(f"  [媒体] 音频已激活（振铃/早期媒体，等待接听）")
                    continue
                if ci.state != pj.PJSIP_INV_STATE_CONFIRMED:
                    continue
                print(f"  [媒体] 音频已激活")
                if not self.audio_setup_done:
                    self.audio_setup_done = True
                    threading.Thread(target=self.setup_audio, daemon=True).start()

    def setup_audio(self):
        try:
            pj.Endpoint.instance().libRegisterThread("setup_audio_thread")
        except:
            pass
        time.sleep(0.5)
        try:
            ci = self.getInfo()
            for i, mi in enumerate(ci.media):
                if mi.type == pj.PJMEDIA_TYPE_AUDIO and mi.status == pj.PJSUA_CALL_MEDIA_ACTIVE:
                    print(f"  [音频] 找到活跃媒体 (index={i})")
                    aud_med = self.getAudioMedia(i)
                    self.audio_port = StreamingAudioPort(self)
                    aud_med.startTransmit(self.audio_port)
                    print("  [音频] ✓ 实时音频接收已连接")
                    if CONFIG.get('recording_enabled'):
                        try:
                            rec_dir = CONFIG.get('recording_dir') or str(SCRIPT_DIR / 'logs' / 'recordings')
                            os.makedirs(rec_dir, exist_ok=True)
                            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                            self._recording_ts = ts
                            self._recording_remote_path = os.path.join(rec_dir, f"_call_{ts}_remote.wav")
                            self._recorder_remote = pj.AudioMediaRecorder()
                            self._recorder_remote.createRecorder(self._recording_remote_path, 0, 0, 0)
                            aud_med.startTransmit(self._recorder_remote)
                            self._aud_med_for_recording = aud_med
                            self.recording_start_time = time.time()
                            self._local_recording = []
                            print(f"  [录音] ✓ 已开启（将保存双方混轨至 {rec_dir}）")
                        except Exception as ex:
                            print(f"  [录音] 开启失败: {ex}")
                    self.play_welcome()
                    self.streaming_asr = StreamingASR(on_sentence_end=self.on_user_speech)
                    self.streaming_asr.start()
                    self.audio_port.is_playing = False
                    print("[系统] ✓ 就绪，等待用户说话...")
                    break
        except Exception as e:
            print(f"  [音频] 设置失败: {e}")
            import traceback
            traceback.print_exc()

    def play_welcome(self):
        intro_text = self.ai.get_introduction()
        print(f"[系统] 播放欢迎语: {intro_text[:40]}...")
        welcome = self.tts.synthesize(intro_text)
        if welcome:
            self.play_audio(welcome, block=True)
            print("[系统] ✓ 欢迎语已播放")

    def _play_audio_worker(self, audio_file):
        try:
            pj.Endpoint.instance().libRegisterThread("playback_thread")
        except Exception:
            pass
        player = None
        aud_med = None
        try:
            if not self.connected:
                return
            if CONFIG.get('recording_enabled') and self.recording_start_time is not None and os.path.exists(audio_file):
                try:
                    with wave.open(audio_file, 'rb') as wf:
                        nch, sw, sr, nf, _, _ = wf.getparams()
                        pcm = wf.readframes(nf)
                    start_offset = time.time() - self.recording_start_time
                    self._local_recording.append((start_offset, pcm, sr))
                except Exception:
                    pass
            with self._playback_lock:
                self._stop_playback = False
            if self.audio_port:
                self.audio_port.is_playing = True
            apply_wav_gain(audio_file, CONFIG.get('playback_gain'))
            player = pj.AudioMediaPlayer()
            player.createPlayer(audio_file, pj.PJMEDIA_FILE_NO_LOOP)
            ci = self.getInfo()
            for i, mi in enumerate(ci.media):
                if mi.type == pj.PJMEDIA_TYPE_AUDIO:
                    aud_med = self.getAudioMedia(i)
                    player.startTransmit(aud_med)
                    file_size = os.path.getsize(audio_file)
                    duration = max(1.0, (file_size - 44) / 32000)
                    print(f"  [播放] {duration:.1f}s")
                    step = 0.1
                    elapsed = 0.0
                    while elapsed < duration + 0.3 and self.connected:
                        if self._stop_playback:
                            print("  [播放] 已打断（用户说话，停止播放）")
                            break
                        time.sleep(step)
                        elapsed += step
                    if aud_med:
                        player.stopTransmit(aud_med)
                    break
        except Exception as e:
            print(f"  [播放] 错误: {e}")
        finally:
            if player:
                try:
                    del player
                except:
                    pass
            if self.audio_port:
                self.audio_port.is_playing = False
            try:
                if os.path.exists(audio_file):
                    os.remove(audio_file)
            except:
                pass

    def play_audio(self, audio_file, block=False):
        if not self.connected:
            return
        t = threading.Thread(target=self._play_audio_worker, args=(audio_file,), daemon=True)
        t.start()
        if block:
            t.join(timeout=60)

    def _flush_playback(self):
        with self._playback_lock:
            self._stop_playback = True

    def _do_hangup_from_thread(self):
        def _run():
            try:
                pj.Endpoint.instance().libRegisterThread("hangup_thread")
            except Exception:
                pass
            if self.hangup_callback:
                self.hangup_callback()
        threading.Thread(target=_run, daemon=True).start()

    def on_user_speech(self, text):
        if not self.connected or not text or not text.strip() or self._is_ending:
            return
        recognized = text.strip()
        if len(recognized) < 2:
            return
        meaningful = ''.join(c for c in recognized if c.isalnum() or c.isspace()).strip()
        if len(meaningful) < 2:
            return
        now = time.time()
        if recognized == self._last_user_speech_text and (now - self._last_user_speech_time) < 10.0:
            return
        self._last_user_speech_text = recognized
        self._last_user_speech_time = now
        recognized_lower = recognized.lower()
        goodbye_matched = [kw for kw in CONFIG['goodbye_keywords'] if kw in recognized_lower]
        if goodbye_matched:
            print(f"\n  [挂断] 检测到再见语: {goodbye_matched}")
            self._is_ending = True
            self._flush_playback()
            time.sleep(0.4)
            if self.audio_port:
                self.audio_port.is_playing = False
            farewell = CONFIG.get('farewell_message', 'Baik, terima kasih. Sampai jumpa.')
            fa = self.tts.synthesize(farewell)
            if fa and self.connected:
                self.play_audio(fa, block=True)
            if self.hangup_callback:
                self._do_hangup_from_thread()
            return
        if self.call_start_time and self.hangup_callback:
            if time.time() - self.call_start_time >= CONFIG['max_call_duration_sec']:
                print(f"\n  [挂断] 已达通话时长上限 ({CONFIG['max_call_duration_sec']}s)")
                self._do_hangup_from_thread()
                return
        if self.audio_port and self.audio_port.is_playing:
            ts = time.time()
            elapsed = (ts - self.call_start_time) if self.call_start_time else 0
            is_short = recognized_lower in CONFIG['non_interrupt_words']
            if is_short:
                print(f"  [打断] 节点=AI播放中 通话秒={elapsed:.1f} 内容=\"{recognized}\" 动作=不触发 原因=简短回应")
                return
            print(f"  [打断] 节点=AI播放中 通话秒={elapsed:.1f} 内容=\"{recognized}\" 动作=已触发打断 已停止当前播放")
            self._flush_playback()
        else:
            elapsed = (time.time() - self.call_start_time) if self.call_start_time else 0
            print(f"  [打断] 节点=空闲 通话秒={elapsed:.1f} 内容=\"{recognized}\" 动作=正常处理")
        threading.Thread(target=self.process_speech, args=(text,), daemon=True).start()

    def process_speech(self, text):
        with self.processing_lock:
            if self.is_processing or not self.connected or self._is_ending:
                return
            self.is_processing = True
        try:
            pj.Endpoint.instance().libRegisterThread("speech_thread")
        except:
            pass
        time.sleep(0.35)
        if not self.connected or self._is_ending:
            self.is_processing = False
            return
        try:
            _trace("PIPELINE", "start", detail=f'用户: "{text[:60]}{"..." if len(text) > 60 else ""}"')
            print(f"\n  👤 用户: {text}")
            print("  [AI] 生成回复...")
            reply = self.ai.get_response(text)
            if reply:
                _trace("PIPELINE", "llm_ok")
                print(f"  🤖 AI: {reply}")
                print("  [TTS] 合成...")
                audio = self.tts.synthesize(reply)
                if audio and self.connected and not self._is_ending:
                    self.play_audio(audio)
                    print("  ✓ 回复已播放")
                    _trace("PIPELINE", "tts_ok")
                else:
                    if not audio:
                        _trace("PIPELINE", "tts_fail", detail="TTS 返回空")
                    else:
                        _trace("PIPELINE", "tts_ok")
            else:
                _trace("PIPELINE", "llm_empty", detail="LLM 无回复")
        except Exception as e:
            print(f"  ✗ 处理失败: {e}")
            _trace("PIPELINE", "fail", error=str(e))
        finally:
            self.is_processing = False


class AccountCallback(pj.Account):
    def __init__(self):
        pj.Account.__init__(self)
        self.current_call = None

    def onRegState(self, prm):
        ai = self.getInfo()
        print(f"[注册] {'成功' if ai.regIsActive else '失败'}")

    def onIncomingCall(self, prm):
        call = CallCallback(self, prm.callId)
        ci = call.getInfo()
        print(f"\n[来电] {ci.remoteUri}")
        call_prm = pj.CallOpParam()
        call_prm.statusCode = 200
        call.answer(call_prm)
        self.current_call = call


# ==================== 主系统（无 STUN）====================
class PJsua2StreamingSystem:
    def __init__(self):
        self.ep = None
        self.acc = None
        self.current_call = None

    def start(self):
        try:
            self.ep = pj.Endpoint()
            self.ep.libCreate()
            ep_cfg = pj.EpConfig()
            # 日志级别: 0=关 1=错误 2=警告 3=信息 4=调试(含大量 playdbuf/capdbuf/SIP 等)。需要排查时改为 4
            ep_cfg.logConfig.level = 3
            ep_cfg.logConfig.consoleLevel = 3
            # 公网服务器版：不配置 STUN
            self.ep.libInit(ep_cfg)

            tp_cfg = pj.TransportConfig()
            tp_cfg.port = 0
            self.ep.transportCreate(pj.PJSIP_TRANSPORT_UDP, tp_cfg)
            if CONFIG.get('sip_transport') == 'tcp':
                tp_cfg_tcp = pj.TransportConfig()
                tp_cfg_tcp.port = 0
                self.ep.transportCreate(pj.PJSIP_TRANSPORT_TCP, tp_cfg_tcp)

            self.ep.libStart()

            acc_cfg = pj.AccountConfig()
            sip_user = CONFIG['sip_user'] or 'anonymous'
            acc_cfg.idUri = f"sip:{sip_user}@{CONFIG['sip_server']}:{CONFIG['sip_port']}"
            acc_cfg.regConfig.registrarUri = ""
            acc_cfg.regConfig.registerOnAdd = False

            if CONFIG.get('sip_password'):
                cred = pj.AuthCredInfo()
                cred.scheme = "digest"
                cred.realm = "*"
                cred.username = CONFIG['sip_user'] or sip_user
                cred.dataType = 0
                cred.data = CONFIG['sip_password']
                acc_cfg.sipConfig.authCreds.append(cred)

            self.acc = AccountCallback()
            self.acc.create(acc_cfg)

            print("\n" + "="*50)
            print("  pjsua2 印尼语 AI 对话 - 公网服务器版（无 STUN）")
            print("  (DashScope 流式 ASR + 打断 + 自动挂断)")
            print("="*50)
            auth_hint = " (无认证)" if not CONFIG.get('sip_password') else ""
            print(f"  SIP: {sip_user}@{CONFIG['sip_server']}:{CONFIG['sip_port']}{auth_hint}")
            if CONFIG.get('sip_prefix'):
                print(f"  拨号前缀: {CONFIG['sip_prefix']}")
            _transport = (CONFIG.get('sip_transport') or 'udp').upper()
            print(f"  拨号传输: {_transport}")
            print("  运行环境: 公网 IP 服务器（未启用 STUN）")
            print("="*50)
            print("\n命令: call <号码> | hangup | quit\n")

            return True
        except Exception as e:
            print(f"启动失败: {e}")
            return False

    def make_call(self, number):
        if self.current_call:
            print("已有通话中")
            return
        prefix = CONFIG.get('sip_prefix') or ''
        dial_number = (prefix + number.strip()).strip()
        transport = CONFIG.get('sip_transport') or 'udp'
        if transport == 'tcp':
            port = CONFIG['sip_tcp_port']
            uri = f"sip:{dial_number}@{CONFIG['sip_server']}:{port};transport=tcp"
        else:
            port = CONFIG['sip_port']
            uri = f"sip:{dial_number}@{CONFIG['sip_server']}:{port}"
        print("=" * 60)
        print("SIP 测试呼叫 - 印度尼西亚线路（公网服务器版）")
        print("=" * 60)
        print(f"服务器: {CONFIG['sip_server']}:{port} ({transport.upper()})")
        print(f"主叫: {CONFIG['sip_user']}  被叫: {dial_number}")
        print(f"SIP URI: {uri}")
        print("=" * 60)
        try:
            self.current_call = CallCallback(
                self.acc,
                hangup_callback=lambda: self.hangup(),
                clear_on_disconnect_callback=lambda: self.clear_current_call()
            )
            call_prm = pj.CallOpParam(True)
            self.current_call.makeCall(uri, call_prm)
        except Exception as e:
            print(f"拨打失败: {e}")
            self.current_call = None

    def clear_current_call(self):
        """仅清空当前通话引用（用于 DISCONNECTED 时，避免对已终止会话再发 BYE）"""
        self.current_call = None

    def hangup(self):
        if self.current_call:
            try:
                prm = pj.CallOpParam()
                self.current_call.hangup(prm)
            except Exception:
                pass
            self.current_call = None
            print("已挂断")

    def run(self):
        while True:
            try:
                cmd = input(">>> ").strip()
                if not cmd:
                    continue
                elif cmd.startswith("call "):
                    self.make_call(cmd[5:].strip())
                elif cmd == "hangup":
                    self.hangup()
                elif cmd in ("quit", "exit", "q"):
                    self.hangup()
                    break
            except KeyboardInterrupt:
                print("\n退出中...")
                break
            except EOFError:
                break
        self.shutdown()

    def shutdown(self):
        print("关闭系统...")
        self.hangup()
        if self.ep:
            self.ep.libDestroy()
        print("已退出")


def main():
    _init_run_log()
    system = PJsua2StreamingSystem()
    if system.start():
        system.run()


if __name__ == "__main__":
    main()

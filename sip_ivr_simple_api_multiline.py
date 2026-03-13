#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sip_ivr_simple_api_multiline.py - 多路并发 IVR（HTTP API 版）

支持同时拨打多个电话，拨通后播放预录音频，播完自动挂断。
通过 HTTP API 触发呼叫、查询状态。
基于 pjsua2，复用 CDR / 通话录音 / 日志基础设施。
适用于公网 IP 服务器（无 NAT/STUN）。

启动:
  python sip_ivr_simple_api_multiline.py

API:
  POST /api/call    {"phone_number": "xxx", "audio_file": "xxx.wav"}
  POST /api/hangup  {"call_id": "xxx"}  (可选 call_id，不传则挂断全部)
  GET  /api/status
  GET  /api/audio/list
  GET  /api/cdr?date=20260303
"""

import pjsua2 as pj
import sys
import os
import time
import threading
import wave
import json
import struct
import atexit
import uuid
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import urllib.request

from dotenv import load_dotenv
load_dotenv()

SCRIPT_DIR = Path(__file__).parent
LOGS_DIR = SCRIPT_DIR / "logs"
os.makedirs(LOGS_DIR, exist_ok=True)

# ==================== 运行日志 ====================
_log_file = None
_original_stdout = None
_original_stderr = None

class _Tee:
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
    global _log_file, _original_stdout, _original_stderr
    if _log_file is not None:
        return
    date_str = datetime.now().strftime("%Y%m%d")
    log_path = LOGS_DIR / f"sip_ivr_simple_{date_str}.log"
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


# ==================== 配置 ====================
CONFIG = {
    'sip_server': os.getenv('SIP_SERVER', '147.139.205.88'),
    'sip_port': int(os.getenv('SIP_PORT', '5060')),
    'sip_tcp_port': int(os.getenv('SIP_TCP_PORT') or os.getenv('SIP_PORT', '5060')),
    'sip_transport': os.getenv('SIP_TRANSPORT', 'udp').lower(),
    'sip_user': os.getenv('SIP_CALLER_NUMBER', '6281479242434'),
    'sip_password': os.getenv('SIP_PASSWORD', ''),
    'sip_prefix': os.getenv('SIP_PREFIX', '13462').strip(),
    'sample_rate': 16000,
    'playback_gain': float(os.getenv('PLAYBACK_GAIN', '2.0')),
    'max_call_duration_sec': int(os.getenv('MAX_CALL_DURATION_SEC', '120')),
    'ring_timeout_sec': int(os.getenv('RING_TIMEOUT_SEC', '35')),
    'ivr_audio_file': os.getenv('IVR_AUDIO_FILE', ''),
    'audio_dir': str(SCRIPT_DIR / 'audio_files'),
    'recording_dir': str(SCRIPT_DIR / 'logs' / 'recordings'),
    'recording_enabled': os.getenv('RECORDING_ENABLED', 'true').lower() in ('1', 'true', 'yes'),
    'hangup_after_play': os.getenv('IVR_HANGUP_AFTER_PLAY', 'true').lower() in ('1', 'true', 'yes'),
    'api_host': os.getenv('API_HOST', '0.0.0.0'),
    'api_port': int(os.getenv('API_PORT', '8088')),
    'max_concurrent_calls': int(os.getenv('MAX_CONCURRENT_CALLS', '10')),
    'recording_remote_gain': float(os.getenv('RECORDING_REMOTE_GAIN', '3.0')),
}

os.makedirs(CONFIG['audio_dir'], exist_ok=True)
if CONFIG.get('recording_enabled'):
    os.makedirs(CONFIG['recording_dir'], exist_ok=True)


# ==================== CDR ====================
CDR_DIR = LOGS_DIR / "cdr"
os.makedirs(CDR_DIR, exist_ok=True)

_SIP_DISPOSITION_MAP = {
    200: ("ANSWERED", "正常挂断"),
    486: ("BUSY", "用户忙"),
    487: ("NO_ANSWER", "请求已取消"),
    480: ("NO_ANSWER", "暂时无法接通"),
    404: ("FAILED", "号码不存在"),
    403: ("FAILED", "禁止呼叫"),
    408: ("NO_ANSWER", "请求超时"),
    603: ("REJECTED", "拒绝接听"),
}

def _new_cdr():
    return {
        "call_id": str(uuid.uuid4()),
        "direction": "outbound",
        "call_type": "ivr",
        "caller": "",
        "callee": "",
        "callee_raw": "",
        "sip_uri": "",
        "sip_server": "",
        "transport": "",
        "ivr_audio_file": "",
        "ivr_audio_duration": 0.0,
        "ts_invite": None,
        "ts_ringing": None,
        "ts_answer": None,
        "ts_hangup": None,
        "duration_ring": 0.0,
        "duration_talk": 0.0,
        "duration_total": 0.0,
        "disposition": "FAILED",
        "hangup_by": "unknown",
        "sip_code": 0,
        "sip_reason": "",
        "hangup_cause": "",
        "ivr_play_started": False,
        "ivr_play_completed": False,
        "ivr_play_duration": 0.0,
        "recording_path": None,
        "recording_sec": 0.0,
    }

def _save_cdr(cdr):
    try:
        date_str = datetime.now().strftime("%Y%m%d")
        cdr_path = CDR_DIR / f"cdr_{date_str}.jsonl"
        def _ts_iso(ts):
            return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts else None
        cdr["ts_invite_iso"] = _ts_iso(cdr.get("ts_invite"))
        cdr["ts_ringing_iso"] = _ts_iso(cdr.get("ts_ringing"))
        cdr["ts_answer_iso"] = _ts_iso(cdr.get("ts_answer"))
        cdr["ts_hangup_iso"] = _ts_iso(cdr.get("ts_hangup"))
        with open(cdr_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(cdr, ensure_ascii=False, default=str) + "\n")
        print(f"[CDR] ✓ 已保存: {cdr_path}")
        print(f"  call_id={cdr['call_id'][:8]}... disposition={cdr['disposition']} "
              f"talk={cdr['duration_talk']:.1f}s played={cdr['ivr_play_completed']}")
    except Exception as e:
        print(f"[CDR] 保存失败: {e}")


# ==================== 音频增益 ====================
def apply_wav_gain(wav_path, gain):
    if gain is None or abs(gain - 1.0) < 0.01:
        return
    try:
        with wave.open(wav_path, 'rb') as wf:
            nch, sampw, sr, nf, _, _ = wf.getparams()
            if sampw != 2:
                return
            frames = wf.readframes(nf)
        fmt = '<%dh' % (len(frames) // 2)
        samples = list(struct.unpack(fmt, frames))
        out = [max(-32767, min(32767, int(round(s * gain)))) for s in samples]
        with wave.open(wav_path, 'wb') as wf:
            wf.setnchannels(nch)
            wf.setsampwidth(sampw)
            wf.setframerate(sr)
            wf.writeframes(struct.pack('<%dh' % len(out), *out))
    except Exception:
        pass


# ==================== 呼叫回调 ====================
class IVRCallCallback(pj.Call):
    def __init__(self, acc, call_id=pj.PJSUA_INVALID_ID, hangup_callback=None,
                 clear_on_disconnect_callback=None, ivr_audio_file=None,
                 callback_url=None):
        pj.Call.__init__(self, acc, call_id)
        self.acc = acc
        self.hangup_callback = hangup_callback
        self.clear_on_disconnect_callback = clear_on_disconnect_callback
        self.ivr_audio_file = ivr_audio_file or ''
        self.callback_url = callback_url
        self.connected = False
        self.audio_setup_done = False
        self.call_start_time = None
        self._user_hangup_initiated = False
        # 录音
        self._recorder_remote = None
        self._aud_med_for_recording = None
        self.recording_start_time = None
        self._recording_remote_path = None
        self._recording_ts = None
        self._ivr_play_offset = None
        self._ivr_original_file = None
        # CDR
        self.cdr = _new_cdr()
        self._tag = self.cdr["call_id"][:8]

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
        print(f"\n[呼叫:{self._tag}] {state_name}")

        if ci.state == pj.PJSIP_INV_STATE_EARLY:
            print(f"  [{self._tag}] 振铃中，等待对方接听...")
            if self.cdr["ts_ringing"] is None:
                self.cdr["ts_ringing"] = time.time()
                ring_timeout = CONFIG.get('ring_timeout_sec', 35)
                def _ring_timeout_check():
                    try:
                        pj.Endpoint.instance().libRegisterThread("ring_timeout")
                    except Exception:
                        pass
                    deadline = time.time() + ring_timeout
                    while time.time() < deadline:
                        if self.connected or self.cdr.get("ts_hangup"):
                            return
                        time.sleep(1)
                    if not self.connected and not self.cdr.get("ts_hangup"):
                        print(f"\n  [{self._tag}] [挂断] 振铃超时 {ring_timeout}s 未接听")
                        self._user_hangup_initiated = True
                        try:
                            call_prm = pj.CallOpParam()
                            call_prm.statusCode = pj.PJSIP_SC_REQUEST_TIMEOUT
                            self.hangup(call_prm)
                        except Exception:
                            pass
                threading.Thread(target=_ring_timeout_check, daemon=True).start()

        elif ci.state == pj.PJSIP_INV_STATE_CONFIRMED:
            self.connected = True
            self.call_start_time = time.time()
            self.cdr["ts_answer"] = self.call_start_time
            print(f"  [{self._tag}] ✓ 通话已接通")
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
                        time.sleep(5)
                        if not self.connected:
                            break
                        if time.time() - self.call_start_time >= CONFIG['max_call_duration_sec']:
                            print(f"\n  [{self._tag}] [挂断] 通话时长已达 {CONFIG['max_call_duration_sec']}s")
                            self._user_hangup_initiated = True
                            self.hangup_callback()
                            break
                threading.Thread(target=_duration_check, daemon=True).start()

        elif ci.state == pj.PJSIP_INV_STATE_DISCONNECTED:
            self.connected = False
            print(f"  [{self._tag}] 通话已结束")
            code = getattr(ci, 'lastStatusCode', 0) or 0
            reason = getattr(ci, 'lastReason', '') or ''
            disp_map = {200: "正常挂断", 486: "用户忙", 487: "请求已取消",
                        480: "暂时无法接通", 404: "号码不存在", 403: "禁止呼叫",
                        408: "请求超时", 603: "拒绝接听"}
            print(f"  [{self._tag}] 原因: {disp_map.get(code, reason or f'代码 {code}')}")

            # CDR 收尾
            self.cdr["ts_hangup"] = time.time()
            self.cdr["sip_code"] = code
            self.cdr["sip_reason"] = reason
            disp_info = _SIP_DISPOSITION_MAP.get(code)
            if disp_info:
                self.cdr["disposition"] = disp_info[0]
                self.cdr["hangup_cause"] = disp_info[1]
            else:
                self.cdr["disposition"] = "ANSWERED" if self.cdr.get("ts_answer") else "FAILED"
                self.cdr["hangup_cause"] = reason or f"代码 {code}"
            if self._user_hangup_initiated:
                self.cdr["hangup_by"] = "system"
            elif self.cdr.get("ts_answer"):
                self.cdr["hangup_by"] = "remote"
            else:
                self.cdr["hangup_by"] = "remote"
            ts_invite = self.cdr.get("ts_invite") or self.cdr["ts_hangup"]
            ts_ring = self.cdr.get("ts_ringing")
            ts_answer = self.cdr.get("ts_answer")
            ts_hangup = self.cdr["ts_hangup"]
            self.cdr["duration_total"] = round(ts_hangup - ts_invite, 2)
            if ts_ring and ts_answer:
                self.cdr["duration_ring"] = round(ts_answer - ts_ring, 2)
            elif ts_ring:
                self.cdr["duration_ring"] = round(ts_hangup - ts_ring, 2)
            if ts_answer:
                self.cdr["duration_talk"] = round(ts_hangup - ts_answer, 2)

            if self.clear_on_disconnect_callback:
                def _finish_and_clear():
                    try:
                        pj.Endpoint.instance().libRegisterThread("disconnected_clear")
                    except Exception:
                        pass
                    self._finalize_recording()
                    _save_cdr(self.cdr)
                    if self.callback_url:
                        _send_webhook(self.callback_url, self.cdr, tag=self._tag)
                    self.clear_on_disconnect_callback()
                threading.Thread(target=_finish_and_clear, daemon=True).start()
            else:
                _save_cdr(self.cdr)
                if self.callback_url:
                    threading.Thread(
                        target=_send_webhook,
                        args=(self.callback_url, self.cdr),
                        kwargs={"tag": self._tag},
                        daemon=True,
                    ).start()

    def onCallMediaState(self, prm):
        ci = self.getInfo()
        for i, mi in enumerate(ci.media):
            if mi.type == pj.PJMEDIA_TYPE_AUDIO and mi.status == pj.PJSUA_CALL_MEDIA_ACTIVE:
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
        except Exception:
            pass
        time.sleep(0.5)
        try:
            ci = self.getInfo()
            for i, mi in enumerate(ci.media):
                if mi.type == pj.PJMEDIA_TYPE_AUDIO and mi.status == pj.PJSUA_CALL_MEDIA_ACTIVE:
                    print(f"  [{self._tag}] [音频] 找到活跃媒体 (index={i})")
                    aud_med = self.getAudioMedia(i)

                    if CONFIG.get('recording_enabled'):
                        try:
                            rec_dir = CONFIG.get('recording_dir') or str(SCRIPT_DIR / 'logs' / 'recordings')
                            os.makedirs(rec_dir, exist_ok=True)
                            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                            self._recording_ts = ts
                            rec_name = f"ivr_call_{ts}_{self._tag}.wav"
                            self._recording_remote_path = os.path.join(rec_dir, rec_name)
                            self._recorder_remote = pj.AudioMediaRecorder()
                            self._recorder_remote.createRecorder(self._recording_remote_path, 0, 0, 0)
                            aud_med.startTransmit(self._recorder_remote)
                            self._aud_med_for_recording = aud_med
                            self.recording_start_time = time.time()
                            print(f"  [{self._tag}] [录音] ✓ 已开启: {self._recording_remote_path}")
                        except Exception as ex:
                            print(f"  [{self._tag}] [录音] 开启失败: {ex}")

                    self._play_ivr_audio(aud_med)
                    break
        except Exception as e:
            print(f"  [{self._tag}] [音频] 设置失败: {e}")
            import traceback
            traceback.print_exc()

    def _play_ivr_audio(self, aud_med):
        """播放预录的 IVR 音频文件"""
        audio_file = self.ivr_audio_file
        if not audio_file or not os.path.exists(audio_file):
            print(f"  [{self._tag}] [IVR] 音频文件不存在或未指定: {audio_file}")
            return

        try:
            with wave.open(audio_file, 'rb') as wf:
                nch, sw, sr, nf, _, _ = wf.getparams()
                duration = nf / sr
            self.cdr["ivr_audio_duration"] = round(duration, 2)
            print(f"  [{self._tag}] [IVR] 音频: {os.path.basename(audio_file)} ({sr}Hz, {nch}ch, {duration:.1f}s)")
        except Exception as e:
            print(f"  [{self._tag}] [IVR] 音频文件格式错误: {e}")
            return

        import shutil
        temp_file = os.path.join(CONFIG['audio_dir'], f"_ivr_play_{self._tag}_{datetime.now().strftime('%H%M%S%f')}.wav")
        shutil.copy2(audio_file, temp_file)
        apply_wav_gain(temp_file, CONFIG.get('playback_gain'))

        player = None
        try:
            player = pj.AudioMediaPlayer()
            player.createPlayer(temp_file, pj.PJMEDIA_FILE_NO_LOOP)
            player.startTransmit(aud_med)
            if self.recording_start_time:
                self._ivr_play_offset = time.time() - self.recording_start_time
                self._ivr_original_file = audio_file
            self.cdr["ivr_play_started"] = True
            play_start = time.time()
            print(f"  [{self._tag}] [IVR] ▶ 正在播放... ({duration:.1f}s)")

            elapsed = 0.0
            step = 0.1
            while elapsed < duration + 0.5 and self.connected:
                time.sleep(step)
                elapsed += step

            player.stopTransmit(aud_med)
            play_elapsed = time.time() - play_start
            self.cdr["ivr_play_duration"] = round(play_elapsed, 2)

            if self.connected:
                self.cdr["ivr_play_completed"] = True
                print(f"  [{self._tag}] [IVR] ✓ 播放完成 ({play_elapsed:.1f}s)")
                if CONFIG.get('hangup_after_play'):
                    print(f"  [{self._tag}] [IVR] 播放完毕，自动挂断...")
                    time.sleep(1)
                    if self.connected and self.hangup_callback:
                        self._user_hangup_initiated = True
                        self.hangup_callback()
            else:
                print(f"  [{self._tag}] [IVR] 播放中断（通话已断开）")
        except Exception as e:
            print(f"  [{self._tag}] [IVR] 播放失败: {e}")
        finally:
            if player:
                try:
                    del player
                except Exception:
                    pass
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception:
                pass

    def _finalize_recording(self):
        """通话结束时停止录音，混合远端+IVR音频后保存"""
        rec_remote = self._recording_remote_path
        if not CONFIG.get('recording_enabled') or not rec_remote:
            return
        try:
            aud = self._aud_med_for_recording
            rec = self._recorder_remote
            if aud and rec:
                try:
                    aud.stopTransmit(rec)
                except Exception:
                    pass
            try:
                self._recorder_remote = None
            except Exception:
                pass
            time.sleep(0.3)

            if not os.path.exists(rec_remote) or os.path.getsize(rec_remote) < 44:
                print(f"  [{self._tag}] [录音] 文件为空或不存在: {rec_remote}")
                return

            ivr_file = self._ivr_original_file
            ivr_offset = self._ivr_play_offset
            if not ivr_file or not os.path.exists(ivr_file) or ivr_offset is None:
                self.cdr["recording_path"] = rec_remote
                try:
                    with wave.open(rec_remote, 'rb') as wf:
                        self.cdr["recording_sec"] = round(wf.getnframes() / wf.getframerate(), 2)
                except Exception:
                    pass
                print(f"  [{self._tag}] [录音] ✓ 已保存(仅远端): {rec_remote} ({self.cdr['recording_sec']:.1f}s)")
                return

            mixed_path = rec_remote.replace('.wav', '_mixed.wav')
            ok = self._mix_recording(rec_remote, ivr_file, ivr_offset, mixed_path)
            if ok:
                self.cdr["recording_path"] = mixed_path
                try:
                    with wave.open(mixed_path, 'rb') as wf:
                        self.cdr["recording_sec"] = round(wf.getnframes() / wf.getframerate(), 2)
                except Exception:
                    pass
                print(f"  [{self._tag}] [录音] ✓ 已保存(混轨): {mixed_path} ({self.cdr['recording_sec']:.1f}s)")
            else:
                self.cdr["recording_path"] = rec_remote
                try:
                    with wave.open(rec_remote, 'rb') as wf:
                        self.cdr["recording_sec"] = round(wf.getnframes() / wf.getframerate(), 2)
                except Exception:
                    pass
                print(f"  [{self._tag}] [录音] ✓ 已保存(仅远端): {rec_remote} ({self.cdr['recording_sec']:.1f}s)")
        except Exception as e:
            print(f"  [{self._tag}] [录音] 保存失败: {e}")

    def _mix_recording(self, remote_path, ivr_path, ivr_offset_sec, out_path):
        """将远端录音与 IVR 音频按时间对齐混合为单轨 WAV"""
        try:
            remote_pcm = None
            r_sr = 8000
            try:
                with wave.open(remote_path, 'rb') as wf:
                    r_nch, r_sw, r_sr, r_nf, _, _ = wf.getparams()
                    remote_pcm = wf.readframes(r_nf)
                if r_sw != 2:
                    remote_pcm = None
            except Exception:
                remote_pcm = None
            if remote_pcm is None:
                with open(remote_path, 'rb') as f:
                    raw = f.read()
                if len(raw) > 44 and raw[:4] == b'RIFF':
                    remote_pcm = raw[44:]
                else:
                    remote_pcm = raw
                r_sr = CONFIG.get('sample_rate', 16000)
                print(f"  [{self._tag}] [录音] 以 raw PCM 读取远端音频 ({len(remote_pcm)} bytes, {r_sr}Hz)")
            if len(remote_pcm) < 2:
                return False

            out_sr = r_sr
            fmt_r = '<%dh' % (len(remote_pcm) // 2)
            remote_samples = list(struct.unpack(fmt_r, remote_pcm[:len(remote_pcm) // 2 * 2]))
            print(f"  [{self._tag}] [录音] 远端轨: {len(remote_samples)} samples ({len(remote_samples)/r_sr:.1f}s @ {r_sr}Hz)")

            with wave.open(ivr_path, 'rb') as wf:
                i_nch, i_sw, i_sr, i_nf, _, _ = wf.getparams()
                ivr_pcm = wf.readframes(i_nf)
            fmt_i = '<%dh' % (len(ivr_pcm) // 2)
            ivr_samples = list(struct.unpack(fmt_i, ivr_pcm[:len(ivr_pcm) // 2 * 2]))

            if i_sr != out_sr and i_sr > 0:
                ratio = out_sr / i_sr
                ivr_samples = [ivr_samples[min(int(i / ratio), len(ivr_samples) - 1)]
                               for i in range(int(len(ivr_samples) * ratio))]
            print(f"  [{self._tag}] [录音] IVR轨: {len(ivr_samples)} samples ({len(ivr_samples)/out_sr:.1f}s @ {out_sr}Hz)")

            # 混轨时长 = 实际通话时长（远端录音长度），不包含对方挂断后未播放的 IVR
            total_len = len(remote_samples)
            start_idx = max(0, int(ivr_offset_sec * out_sr))

            remote_gain = CONFIG.get('recording_remote_gain', 3.0)
            print(f"  [{self._tag}] [录音] 远端增益: {remote_gain}x")

            mixed = []
            for i in range(total_len):
                r_val = remote_samples[i] if i < len(remote_samples) else 0
                r_val = int(r_val * remote_gain)
                i_val = 0
                ivr_idx = i - start_idx
                if 0 <= ivr_idx < len(ivr_samples):
                    i_val = ivr_samples[ivr_idx]
                sample = r_val + i_val
                mixed.append(max(-32767, min(32767, sample)))

            print(f"  [{self._tag}] [录音] 混轨完成: {len(mixed)/out_sr:.1f}s")
            fmt_out = '<%dh' % len(mixed)
            with wave.open(out_path, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(out_sr)
                wf.writeframes(struct.pack(fmt_out, *mixed))
            return True
        except Exception as e:
            print(f"  [{self._tag}] [录音] 混轨失败: {e}")
            return False


def _send_webhook(callback_url, cdr, tag="????", max_retries=3):
    """通话结束后向 callback_url 发送 CDR，带重试"""
    def _ts_iso(ts):
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts else None

    payload = {
        "event": "call_completed",
        "call_id": cdr.get("call_id", ""),
        "phone_number": cdr.get("callee_raw", ""),
        "callee": cdr.get("callee", ""),
        "caller": cdr.get("caller", ""),
        "disposition": cdr.get("disposition", ""),
        "sip_code": cdr.get("sip_code", 0),
        "sip_reason": cdr.get("sip_reason", ""),
        "hangup_by": cdr.get("hangup_by", ""),
        "hangup_cause": cdr.get("hangup_cause", ""),
        "duration_ring": cdr.get("duration_ring", 0),
        "duration_talk": cdr.get("duration_talk", 0),
        "duration_total": cdr.get("duration_total", 0),
        "ivr_audio_file": cdr.get("ivr_audio_file", ""),
        "ivr_play_started": cdr.get("ivr_play_started", False),
        "ivr_play_completed": cdr.get("ivr_play_completed", False),
        "ivr_play_duration": cdr.get("ivr_play_duration", 0),
        "recording_path": cdr.get("recording_path"),
        "recording_sec": cdr.get("recording_sec", 0),
        "ts_invite": _ts_iso(cdr.get("ts_invite")),
        "ts_ringing": _ts_iso(cdr.get("ts_ringing")),
        "ts_answer": _ts_iso(cdr.get("ts_answer")),
        "ts_hangup": _ts_iso(cdr.get("ts_hangup")),
    }

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    delays = [3, 10, 30]

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                callback_url,
                data=body,
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                status = resp.getcode()
                if 200 <= status < 300:
                    print(f"  [{tag}] [回调] ✓ 已推送 CDR → {callback_url} (HTTP {status})")
                    return True
                else:
                    print(f"  [{tag}] [回调] 响应异常 HTTP {status}，第 {attempt+1}/{max_retries} 次")
        except Exception as e:
            print(f"  [{tag}] [回调] 发送失败: {e}，第 {attempt+1}/{max_retries} 次")

        if attempt < max_retries - 1:
            wait = delays[min(attempt, len(delays) - 1)]
            print(f"  [{tag}] [回调] {wait}s 后重试...")
            time.sleep(wait)

    print(f"  [{tag}] [回调] ✗ 全部 {max_retries} 次重试失败，放弃推送")
    return False


# ==================== 账号回调 ====================
class AccountCallback(pj.Account):
    def __init__(self):
        pj.Account.__init__(self)

    def onRegState(self, prm):
        ai = self.getInfo()
        print(f"[注册] {'成功' if ai.regIsActive else '失败'}")

    def onIncomingCall(self, prm):
        call = IVRCallCallback(self, prm.callId)
        ci = call.getInfo()
        print(f"\n[来电] {ci.remoteUri} — IVR 不处理来电，拒绝")
        call_prm = pj.CallOpParam()
        call_prm.statusCode = 486
        call.answer(call_prm)


# ==================== 主系统 ====================
class IVRSystem:
    def __init__(self):
        self.ep = None
        self.acc = None
        self.active_calls = {}       # call_id → IVRCallCallback
        self._calls_lock = threading.Lock()

    def start(self):
        try:
            self.ep = pj.Endpoint()
            self.ep.libCreate()
            ep_cfg = pj.EpConfig()
            ep_cfg.logConfig.level = 3
            ep_cfg.logConfig.consoleLevel = 3
            ep_cfg.uaConfig.maxCalls = CONFIG['max_concurrent_calls']
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

            ivr_audio = CONFIG.get('ivr_audio_file') or ''
            audio_status = f"✓ {ivr_audio}" if ivr_audio and os.path.exists(ivr_audio) else "✗ 未设置（使用 call 命令时可指定）"
            max_conc = CONFIG['max_concurrent_calls']

            print("\n" + "=" * 50)
            print("  多路并发 IVR 系统 - HTTP API 版（无 STUN）")
            print("  拨通后播放预录音频，播完自动挂断")
            print("=" * 50)
            auth_hint = " (无认证)" if not CONFIG.get('sip_password') else ""
            print(f"  SIP: {sip_user}@{CONFIG['sip_server']}:{CONFIG['sip_port']}{auth_hint}")
            if CONFIG.get('sip_prefix'):
                print(f"  拨号前缀: {CONFIG['sip_prefix']}")
            _transport = (CONFIG.get('sip_transport') or 'udp').upper()
            print(f"  传输协议: {_transport}")
            print(f"  最大并发: {max_conc} 路")
            print(f"  振铃超时: {CONFIG['ring_timeout_sec']}s")
            print(f"  IVR 音频: {audio_status}")
            print(f"  音频目录: {CONFIG['audio_dir']}")
            print(f"  播放增益: {CONFIG['playback_gain']}x")
            print(f"  播完挂断: {'是' if CONFIG.get('hangup_after_play') else '否'}")
            print(f"  通话录音: {'开' if CONFIG.get('recording_enabled') else '关'}")
            print(f"  API 端口: {CONFIG['api_port']}")
            print("=" * 50)

            return True
        except Exception as e:
            print(f"启动失败: {e}")
            return False

    def _resolve_audio(self, audio_file):
        """解析音频文件路径，返回绝对路径或 None"""
        ivr_audio = audio_file or CONFIG.get('ivr_audio_file') or ''
        if not ivr_audio:
            return None
        if not os.path.isabs(ivr_audio):
            for c in [str(SCRIPT_DIR / ivr_audio), os.path.join(CONFIG['audio_dir'], ivr_audio)]:
                if os.path.exists(c):
                    return c
        if os.path.exists(ivr_audio):
            return ivr_audio
        return None

    def list_audio_files(self):
        """列出 audio_files/ 下的可用 WAV 文件"""
        audio_dir = CONFIG['audio_dir']
        result = []
        if os.path.isdir(audio_dir):
            for f in sorted(os.listdir(audio_dir)):
                if f.lower().endswith('.wav') and not f.startswith('_'):
                    info = {"name": f}
                    try:
                        with wave.open(os.path.join(audio_dir, f), 'rb') as wf:
                            info["sample_rate"] = wf.getframerate()
                            info["duration"] = round(wf.getnframes() / wf.getframerate(), 1)
                            info["channels"] = wf.getnchannels()
                    except Exception:
                        info["error"] = "格式异常"
                    result.append(info)
        return result

    def get_status(self):
        """获取所有活跃通话的状态"""
        self._ensure_thread_registered()
        with self._calls_lock:
            calls_snapshot = list(self.active_calls.values())
        calls_info = []
        for call in calls_snapshot:
            try:
                cdr = call.cdr
                calls_info.append({
                    "call_id": cdr.get("call_id", ""),
                    "callee": cdr.get("callee", ""),
                    "callee_raw": cdr.get("callee_raw", ""),
                    "audio_file": cdr.get("ivr_audio_file", ""),
                    "connected": call.connected,
                    "play_started": cdr.get("ivr_play_started", False),
                    "play_completed": cdr.get("ivr_play_completed", False),
                })
            except Exception:
                pass
        return {
            "active_calls": len(calls_info),
            "max_concurrent": CONFIG['max_concurrent_calls'],
            "calls": calls_info,
        }

    def _ensure_thread_registered(self):
        try:
            pj.Endpoint.instance().libRegisterThread("api_thread")
        except Exception:
            pass

    def make_call(self, number, audio_file=None, callback_url=None):
        """发起呼叫，返回 (success, call_id_or_error)"""
        self._ensure_thread_registered()
        max_conc = CONFIG['max_concurrent_calls']
        with self._calls_lock:
            if len(self.active_calls) >= max_conc:
                return False, f"已达最大并发数 {max_conc}，当前 {len(self.active_calls)} 路通话中"

        ivr_audio = self._resolve_audio(audio_file)
        if not ivr_audio:
            avail = [f["name"] for f in self.list_audio_files()]
            return False, f"音频文件不存在: {audio_file or '(未指定)'}。可用: {avail}"

        prefix = CONFIG.get('sip_prefix') or ''
        dial_number = (prefix + number.strip()).strip()
        transport = CONFIG.get('sip_transport') or 'udp'
        if transport == 'tcp':
            port = CONFIG['sip_tcp_port']
            uri = f"sip:{dial_number}@{CONFIG['sip_server']}:{port};transport=tcp"
        else:
            port = CONFIG['sip_port']
            uri = f"sip:{dial_number}@{CONFIG['sip_server']}:{port}"

        try:
            callback = IVRCallCallback(
                self.acc,
                hangup_callback=None,
                clear_on_disconnect_callback=None,
                ivr_audio_file=ivr_audio,
                callback_url=callback_url,
            )
            call_id = callback.cdr["call_id"]
            tag = callback._tag

            callback.hangup_callback = lambda cid=call_id: self.hangup(cid)
            callback.clear_on_disconnect_callback = lambda cid=call_id: self._remove_call(cid)

            callback.cdr["caller"] = CONFIG['sip_user']
            callback.cdr["callee"] = dial_number
            callback.cdr["callee_raw"] = number.strip()
            callback.cdr["sip_uri"] = uri
            callback.cdr["sip_server"] = f"{CONFIG['sip_server']}:{port}"
            callback.cdr["transport"] = transport.upper()
            callback.cdr["ivr_audio_file"] = os.path.basename(ivr_audio)
            callback.cdr["ts_invite"] = time.time()

            with self._calls_lock:
                if len(self.active_calls) >= max_conc:
                    return False, f"已达最大并发数 {max_conc}"
                self.active_calls[call_id] = callback

            active_count = len(self.active_calls)
            print(f"\n[IVR:{tag}] 发起呼叫 ({active_count}/{max_conc})")
            print(f"  被叫: {dial_number}  音频: {os.path.basename(ivr_audio)}")
            print(f"  URI: {uri}")

            call_prm = pj.CallOpParam(True)
            callback.makeCall(uri, call_prm)
            return True, call_id
        except Exception as e:
            err_msg = str(e).strip() or type(e).__name__
            print(f"拨打失败: {err_msg}")
            with self._calls_lock:
                self.active_calls.pop(call_id, None)
            return False, err_msg

    def _remove_call(self, call_id):
        """通话结束后从活跃列表移除"""
        with self._calls_lock:
            self.active_calls.pop(call_id, None)
            remaining = len(self.active_calls)
        print(f"[系统] 通话 {call_id[:8]}... 已清理，剩余活跃: {remaining}")

    def hangup(self, call_id=None):
        """挂断指定通话，不传 call_id 则挂断全部"""
        self._ensure_thread_registered()
        if call_id:
            with self._calls_lock:
                call = self.active_calls.get(call_id)
            if call:
                try:
                    call._user_hangup_initiated = True
                    prm = pj.CallOpParam()
                    call.hangup(prm)
                except Exception:
                    pass
                print(f"[系统] 已挂断通话 {call_id[:8]}...")
                return True, call_id
            return False, f"通话不存在: {call_id}"
        else:
            with self._calls_lock:
                all_calls = list(self.active_calls.items())
            if not all_calls:
                return False, "没有活动的呼叫"
            hung_up = []
            for cid, call in all_calls:
                try:
                    call._user_hangup_initiated = True
                    prm = pj.CallOpParam()
                    call.hangup(prm)
                    hung_up.append(cid)
                except Exception:
                    pass
            print(f"[系统] 已挂断全部 {len(hung_up)} 路通话")
            return True, f"已挂断 {len(hung_up)} 路通话"

    def shutdown(self):
        print("关闭系统...")
        self.hangup()
        time.sleep(1)
        if self.ep:
            self.ep.libDestroy()
        print("已退出")


# ==================== HTTP API ====================
class IVRAPIHandler(BaseHTTPRequestHandler):
    ivr_system = None

    def _read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8') if length > 0 else ''
        try:
            return json.loads(body) if body else {}
        except Exception:
            return {}

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode('utf-8'))

    def do_OPTIONS(self):
        self._send_json({})

    def do_POST(self):
        path = urlparse(self.path).path
        data = self._read_body()

        if path == '/api/call':
            self._handle_call(data)
        elif path == '/api/hangup':
            self._handle_hangup(data)
        else:
            self._send_json({"success": False, "error": f"未知接口: {path}"}, 404)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path == '/api/status':
            self._handle_status()
        elif path == '/api/audio/list':
            self._handle_audio_list()
        elif path == '/api/cdr':
            self._handle_cdr(params)
        elif path == '/':
            self._handle_dashboard()
        else:
            self._send_json({"success": False, "error": f"未知接口: {path}"}, 404)

    def _handle_call(self, data):
        phone_number = data.get('phone_number', '').strip()
        audio_file = data.get('audio_file', '').strip() or None
        callback_url = data.get('callback_url', '').strip() or None
        if not phone_number:
            self._send_json({"success": False, "error": "缺少 phone_number 参数"}, 400)
            return
        ok, result = self.ivr_system.make_call(phone_number, audio_file, callback_url=callback_url)
        if ok:
            status = self.ivr_system.get_status()
            self._send_json({
                "success": True,
                "message": "呼叫已发起",
                "call_id": result,
                "phone_number": phone_number,
                "audio_file": audio_file or CONFIG.get('ivr_audio_file', ''),
                "active_calls": status["active_calls"],
                "max_concurrent": status["max_concurrent"],
            })
        else:
            self._send_json({"success": False, "error": result}, 400)

    def _handle_hangup(self, data=None):
        data = data or {}
        call_id = data.get('call_id', '').strip() if isinstance(data, dict) else ''
        ok, result = self.ivr_system.hangup(call_id or None)
        if ok:
            self._send_json({"success": True, "message": result if isinstance(result, str) else "已挂断", "call_id": result})
        else:
            self._send_json({"success": False, "error": result}, 400)

    def _handle_status(self):
        status = self.ivr_system.get_status()
        self._send_json({"success": True, **status})

    def _handle_audio_list(self):
        files = self.ivr_system.list_audio_files()
        self._send_json({"success": True, "audio_dir": CONFIG['audio_dir'], "files": files})

    def _handle_cdr(self, params):
        date = params.get('date', [None])[0]
        if not date:
            date = datetime.now().strftime("%Y%m%d")
        cdr_path = CDR_DIR / f"cdr_{date}.jsonl"
        if not cdr_path.exists():
            self._send_json({"success": True, "date": date, "records": [], "count": 0})
            return
        records = []
        try:
            with open(cdr_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))
        except Exception as e:
            self._send_json({"success": False, "error": str(e)}, 500)
            return
        self._send_json({"success": True, "date": date, "records": records, "count": len(records)})

    def _handle_dashboard(self):
        html = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>IVR 多路并发控制面板</title>
<style>
  * { box-sizing: border-box; }
  body { font-family: -apple-system, Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; background: #f5f5f5; }
  h1 { color: #333; margin-bottom: 5px; }
  .subtitle { color: #888; margin-bottom: 25px; }
  .card { background: #fff; border-radius: 8px; padding: 20px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
  label { font-weight: 600; display: block; margin-bottom: 4px; color: #555; }
  input { width: 100%%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 15px; margin-bottom: 12px; }
  .btn-row { display: flex; gap: 10px; }
  button { flex: 1; padding: 12px; font-size: 15px; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; }
  .btn-call { background: #4CAF50; color: #fff; }
  .btn-call:hover { background: #43a047; }
  .btn-hangup { background: #f44336; color: #fff; }
  .btn-hangup:hover { background: #e53935; }
  .btn-status { background: #2196F3; color: #fff; }
  .btn-status:hover { background: #1e88e5; }
  .btn-sm { flex: none; padding: 6px 14px; font-size: 12px; border-radius: 4px; }
  #calls-panel { margin-bottom: 16px; }
  .call-row { display: flex; align-items: center; gap: 10px; padding: 8px 12px; background: #e8f5e9; border-radius: 6px; margin-bottom: 6px; font-size: 13px; }
  .call-row.ringing { background: #fff3e0; }
  .call-row .cid { font-family: monospace; color: #555; }
  .call-row .callee { font-weight: 600; }
  .call-row .status { margin-left: auto; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }
  .badge-ok { background: #c8e6c9; color: #2e7d32; }
  .badge-ring { background: #ffe0b2; color: #e65100; }
  .badge-play { background: #bbdefb; color: #1565c0; }
  .counter { font-size: 14px; color: #666; margin-bottom: 10px; }
  #log { background: #1e1e1e; color: #d4d4d4; padding: 16px; border-radius: 8px; height: 280px; overflow-y: auto; font-family: 'Menlo', monospace; font-size: 13px; line-height: 1.5; }
  .log-ok { color: #4ec9b0; } .log-err { color: #f48771; } .log-info { color: #9cdcfe; }
</style></head><body>
<h1>IVR 多路并发控制面板</h1>
<p class="subtitle">支持同时拨打多个电话，播放预录音频后自动挂断</p>
<div class="card">
  <label>被叫号码</label>
  <input type="text" id="phone" placeholder="例如: 82121065486">
  <label>音频文件（留空则使用默认）</label>
  <input type="text" id="audio" placeholder="例如: reminder.wav">
  <div class="btn-row">
    <button class="btn-call" onclick="makeCall()">拨号</button>
    <button class="btn-hangup" onclick="hangupAll()">全部挂断</button>
    <button class="btn-status" onclick="refreshStatus()">刷新状态</button>
  </div>
</div>
<div class="card" id="calls-panel">
  <div class="counter" id="counter">活跃通话: 0 / -</div>
  <div id="calls-list"><span style="color:#aaa">暂无活跃通话</span></div>
</div>
<div id="log">系统就绪，等待操作...</div>
<script>
function log(msg, cls) {
  const el = document.getElementById('log');
  const t = new Date().toLocaleTimeString();
  el.innerHTML += '<div class="' + (cls||'') + '">[' + t + '] ' + msg + '</div>';
  el.scrollTop = el.scrollHeight;
}
function api(method, path, body) {
  const opts = { method, headers: {'Content-Type':'application/json'} };
  if (body) opts.body = JSON.stringify(body);
  return fetch(path, opts).then(r => r.json());
}
function makeCall() {
  const phone = document.getElementById('phone').value.trim();
  if (!phone) { alert('请输入号码'); return; }
  const audio = document.getElementById('audio').value.trim() || undefined;
  log('拨打 ' + phone + (audio ? ' (' + audio + ')' : '') + '...', 'log-info');
  api('POST', '/api/call', {phone_number: phone, audio_file: audio})
    .then(d => {
      if (d.success) {
        log('呼叫已发起 call_id=' + d.call_id.substring(0,8) + '... (' + d.active_calls + '/' + d.max_concurrent + ')', 'log-ok');
        refreshStatus();
      } else {
        log('失败: ' + d.error, 'log-err');
      }
    })
    .catch(e => log('请求错误: ' + e, 'log-err'));
}
function hangupAll() {
  log('挂断全部...', 'log-info');
  api('POST', '/api/hangup', {})
    .then(d => { log(d.success ? d.message : d.error, d.success ? 'log-ok' : 'log-err'); setTimeout(refreshStatus, 1500); })
    .catch(e => log('请求错误: ' + e, 'log-err'));
}
function hangupOne(callId) {
  log('挂断 ' + callId.substring(0,8) + '...', 'log-info');
  api('POST', '/api/hangup', {call_id: callId})
    .then(d => { log(d.success ? '已挂断 ' + callId.substring(0,8) : d.error, d.success ? 'log-ok' : 'log-err'); setTimeout(refreshStatus, 1500); })
    .catch(e => log('请求错误: ' + e, 'log-err'));
}
function refreshStatus() {
  api('GET', '/api/status').then(d => {
    document.getElementById('counter').textContent = '活跃通话: ' + d.active_calls + ' / ' + d.max_concurrent;
    const list = document.getElementById('calls-list');
    if (!d.calls || d.calls.length === 0) {
      list.innerHTML = '<span style="color:#aaa">暂无活跃通话</span>';
      return;
    }
    let html = '';
    d.calls.forEach(c => {
      const st = c.play_completed ? '播放完成' : c.play_started ? '播放中' : c.connected ? '已接通' : '拨号中';
      const cls = c.connected ? '' : ' ringing';
      const badge = c.play_started ? 'badge-play' : c.connected ? 'badge-ok' : 'badge-ring';
      html += '<div class="call-row' + cls + '">'
        + '<span class="cid">' + c.call_id.substring(0,8) + '</span>'
        + '<span class="callee">' + (c.callee_raw || c.callee) + '</span>'
        + '<span class="status"><span class="badge ' + badge + '">' + st + '</span></span>'
        + '<button class="btn-hangup btn-sm" onclick="hangupOne(\\'' + c.call_id + '\\')">挂断</button>'
        + '</div>';
    });
    list.innerHTML = html;
  }).catch(e => log('刷新失败: ' + e, 'log-err'));
}
setInterval(refreshStatus, 3000);
refreshStatus();
</script></body></html>"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def log_message(self, format, *args):
        pass


def _run_api_server(ivr_system):
    IVRAPIHandler.ivr_system = ivr_system
    host = CONFIG['api_host']
    port = CONFIG['api_port']
    server = HTTPServer((host, port), IVRAPIHandler)
    print(f"[API] ✓ HTTP API 已启动: http://{host}:{port}")
    print(f"  控制面板: http://localhost:{port}/")
    print(f"  接口列表:")
    print(f"    POST /api/call     — 发起呼叫 (支持并发)")
    print(f"    POST /api/hangup   — 挂断通话 (可选 call_id，不传则挂断全部)")
    print(f"    GET  /api/status   — 查询所有活跃通话")
    print(f"    GET  /api/audio/list — 列出音频")
    print(f"    GET  /api/cdr?date=YYYYMMDD — 查询CDR")
    try:
        server.serve_forever()
    except Exception:
        pass


def main():
    _init_run_log()
    system = IVRSystem()
    if not system.start():
        sys.exit(1)

    api_thread = threading.Thread(target=_run_api_server, args=(system,), daemon=True)
    api_thread.start()

    print("\n服务已启动，按 Ctrl+C 停止\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n退出中...")
    finally:
        system.shutdown()


if __name__ == "__main__":
    main()

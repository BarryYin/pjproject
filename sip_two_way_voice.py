#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双向语音通信系统 - 完整方案
支持三种模式:
1. 麦克风模式 (MICROPHONE) - 实时麦克风输入/扬声器输出
2. 音频队列模式 (AUDIO_QUEUE) - 预录音频文件队列播放
3. 混合模式 (HYBRID) - 队列播放 + 录制对方语音

基于PJSIP底层音频桥接 (Conference Bridge) 实现
"""

import sys
import time
import pjsua as pj
import threading
import os
import json
import queue
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from enum import Enum

# ==================== 配置 ====================

CONFIG = {
    'server': '147.139.205.88',
    'port': 5060,
    'caller_number': '6281479242434',
    'prefix': '13462',
    'log_level': 3,
    
    # 音频文件路径
    'audio_dir': '/home/henry/pjproject/audio_files',
    'recordings_dir': '/home/henry/pjproject/recordings',
    
    # HTTP API配置
    'api_host': '0.0.0.0',
    'api_port': 8088,
    
    # 默认通信模式
    'default_mode': 'AUDIO_QUEUE'  # MICROPHONE / AUDIO_QUEUE / HYBRID
}


class VoiceMode(Enum):
    """语音通信模式"""
    MICROPHONE = "microphone"      # 实时麦克风模式
    AUDIO_QUEUE = "audio_queue"    # 音频队列模式
    HYBRID = "hybrid"              # 混合模式


# ==================== 音频队列管理器 ====================

class AudioQueueManager:
    """音频队列管理器 - 管理待播放的音频文件"""
    
    def __init__(self, audio_dir):
        self.audio_dir = audio_dir
        self.queue = queue.Queue()
        self.current_player = None
        self.current_player_id = None
        self.is_playing = False
        self.lock = threading.Lock()
        
    def add_audio(self, filename):
        """添加音频文件到队列"""
        audio_path = os.path.join(self.audio_dir, filename)
        if not os.path.exists(audio_path):
            print(f"  [音频队列] 文件不存在: {filename}")
            return False
        
        self.queue.put(audio_path)
        print(f"  [音频队列] 已添加: {filename} (队列长度: {self.queue.qsize()})")
        return True
    
    def add_audio_path(self, audio_path):
        """添加完整路径的音频文件到队列"""
        if not os.path.exists(audio_path):
            print(f"  [音频队列] 文件不存在: {audio_path}")
            return False
        
        self.queue.put(audio_path)
        print(f"  [音频队列] 已添加: {os.path.basename(audio_path)} (队列长度: {self.queue.qsize()})")
        return True
    
    def has_next(self):
        """检查是否还有待播放的音频"""
        return not self.queue.empty()
    
    def get_next(self):
        """获取下一个待播放的音频"""
        try:
            return self.queue.get_nowait()
        except queue.Empty:
            return None
    
    def clear(self):
        """清空队列"""
        with self.lock:
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                except queue.Empty:
                    break
        print("  [音频队列] 已清空")
    
    def get_queue_size(self):
        """获取队列长度"""
        return self.queue.qsize()


# ==================== 双向语音回调 ====================

class TwoWayVoiceCallback(pj.CallCallback):
    """双向语音通信回调"""
    
    def __init__(self, call=None, voice_system=None, mode=VoiceMode.AUDIO_QUEUE):
        pj.CallCallback.__init__(self, call)
        self.voice_system = voice_system
        self.mode = mode
        
        # 呼叫状态
        self.call_connected = False
        self.call_ended = False
        self.start_time = time.time()
        self.connect_time = None
        
        # 音频播放器和录音器
        self.current_player = None
        self.current_player_id = None
        self.recorder = None
        self.recorder_id = None
        
        # 音频队列管理
        self.audio_queue = AudioQueueManager(CONFIG['audio_dir'])
        self.auto_play_thread = None
        self.auto_play_running = False
        
    def on_state(self):
        """呼叫状态变化"""
        info = self.call.info()
        elapsed = time.time() - self.start_time
        
        print(f"\n[{elapsed:.1f}s] 呼叫状态: {info.state_text}")
        print(f"  远程: {info.remote_uri}")
        print(f"  响应: {info.last_code} ({info.last_reason})")
        print(f"  模式: {self.mode.value}")
        
        if info.state == pj.CallState.CONFIRMED:
            self.call_connected = True
            self.connect_time = time.time()
            print("  >>> 呼叫已接通!")
            
            # 通知系统呼叫已接通
            if self.voice_system:
                self.voice_system.command_queue.put(('call_connected', self))
            
        elif info.state == pj.CallState.DISCONNECTED:
            self.call_ended = True
            duration = time.time() - self.start_time
            print(f"  >>> 呼叫结束 (总时长: {duration:.1f}秒)")
            
            # 清理资源
            self.cleanup()
            
    def on_media_state(self):
        """媒体状态变化 - 音频桥接配置"""
        info = self.call.info()
        
        if info.media_state == pj.MediaState.ACTIVE:
            call_slot = info.conf_slot
            
            print(f"\n  [媒体] 音频桥接配置 (模式: {self.mode.value})")
            
            if self.mode == VoiceMode.MICROPHONE:
                # 麦克风模式: 直接连接麦克风和扬声器
                # Slot 0 = 本地音频设备 (麦克风 + 扬声器)
                pj.Lib.instance().conf_connect(call_slot, 0)  # 对方声音 → 本地扬声器
                pj.Lib.instance().conf_connect(0, call_slot)  # 本地麦克风 → 对方
                print("  [媒体] ✓ 麦克风模式: 双向连接已建立")
                print("  [媒体]   - 对方声音 → 本地扬声器")
                print("  [媒体]   - 本地麦克风 → 对方")
                
            elif self.mode == VoiceMode.AUDIO_QUEUE:
                # 音频队列模式: 只接收对方声音到扬声器，发送通过播放器
                pj.Lib.instance().conf_connect(call_slot, 0)  # 对方声音 → 本地扬声器
                print("  [媒体] ✓ 音频队列模式: 接收通道已建立")
                print("  [媒体]   - 对方声音 → 本地扬声器")
                print("  [媒体]   - 发送通过音频队列播放器")
                
            elif self.mode == VoiceMode.HYBRID:
                # 混合模式: 接收对方声音 + 队列播放
                pj.Lib.instance().conf_connect(call_slot, 0)  # 对方声音 → 本地扬声器
                print("  [媒体] ✓ 混合模式: 接收通道已建立")
                print("  [媒体]   - 对方声音 → 本地扬声器")
                print("  [媒体]   - 发送通过音频队列播放器")
            
            print()
    
    def play_audio_file(self, audio_path):
        """播放音频文件给对方"""
        try:
            info = self.call.info()
            if info.state != pj.CallState.CONFIRMED:
                print("  [播放] 呼叫未接通，无法播放")
                return False
            
            # 停止当前播放
            self.stop_current_player()
            
            # 创建新播放器
            self.current_player = pj.Lib.instance().create_player(audio_path, loop=False)
            self.current_player_id = pj.Lib.instance().player_get_slot(self.current_player)
            
            # 连接播放器到呼叫
            pj.Lib.instance().conf_connect(self.current_player_id, info.conf_slot)
            
            filename = os.path.basename(audio_path)
            print(f"  [播放] ✓ 正在播放: {filename}")
            return True
            
        except Exception as e:
            print(f"  [播放] ✗ 失败: {e}")
            return False
    
    def stop_current_player(self):
        """停止当前播放器"""
        if self.current_player:
            try:
                info = self.call.info()
                pj.Lib.instance().conf_disconnect(self.current_player_id, info.conf_slot)
                self.current_player = None
                self.current_player_id = None
            except:
                pass
    
    def start_recording(self, record_file):
        """开始录音"""
        try:
            info = self.call.info()
            if info.state != pj.CallState.CONFIRMED:
                print("  [录音] 呼叫未接通，无法录音")
                return False
            
            # 停止之前的录音
            self.stop_recording()
            
            # 创建录音器
            self.recorder = pj.Lib.instance().create_recorder(record_file)
            self.recorder_id = pj.Lib.instance().recorder_get_slot(self.recorder)
            
            # 连接音频源到录音器
            pj.Lib.instance().conf_connect(info.conf_slot, self.recorder_id)  # 对方声音
            pj.Lib.instance().conf_connect(0, self.recorder_id)  # 本地声音
            
            print(f"  [录音] ✓ 开始录制: {os.path.basename(record_file)}")
            return True
            
        except Exception as e:
            print(f"  [录音] ✗ 失败: {e}")
            return False
    
    def stop_recording(self):
        """停止录音"""
        if self.recorder:
            try:
                info = self.call.info()
                pj.Lib.instance().conf_disconnect(info.conf_slot, self.recorder_id)
                pj.Lib.instance().conf_disconnect(0, self.recorder_id)
                self.recorder = None
                self.recorder_id = None
                print("  [录音] 已停止")
                return True
            except Exception as e:
                print(f"  [录音] 停止失败: {e}")
                return False
        return False
    
    def add_to_queue(self, filename):
        """添加音频到播放队列"""
        return self.audio_queue.add_audio(filename)
    
    def start_auto_play(self):
        """启动自动播放线程 - 自动播放队列中的音频"""
        if self.auto_play_running:
            print("  [自动播放] 已在运行")
            return
        
        self.auto_play_running = True
        self.auto_play_thread = threading.Thread(target=self._auto_play_loop, daemon=True)
        self.auto_play_thread.start()
        print("  [自动播放] ✓ 已启动")
    
    def stop_auto_play(self):
        """停止自动播放"""
        self.auto_play_running = False
        print("  [自动播放] 已停止")
    
    def _auto_play_loop(self):
        """自动播放循环"""
        print("  [自动播放] 线程已启动")
        
        while self.auto_play_running and not self.call_ended:
            # 检查是否有待播放的音频
            if self.audio_queue.has_next():
                audio_path = self.audio_queue.get_next()
                if audio_path:
                    self.play_audio_file(audio_path)
                    
                    # 等待播放完成（简单估算，每秒8000采样）
                    # 实际应该监听播放器状态
                    time.sleep(3)  # 预估播放时间
            
            time.sleep(0.5)
        
        print("  [自动播放] 线程已退出")
    
    def cleanup(self):
        """清理资源"""
        self.stop_auto_play()
        self.stop_current_player()
        self.stop_recording()
        self.audio_queue.clear()


# ==================== 双向语音系统 ====================

class TwoWayVoiceSystem:
    """双向语音通信系统"""
    
    def __init__(self, mode=VoiceMode.AUDIO_QUEUE):
        self.lib = None
        self.acc = None
        self.transport = None
        self.current_call = None
        self.current_callback = None
        self.mode = mode
        
        # 命令队列 - 线程安全通信
        self.command_queue = queue.Queue()
        self.result_queue = queue.Queue()
        
        # 创建必要的目录
        os.makedirs(CONFIG['audio_dir'], exist_ok=True)
        os.makedirs(CONFIG['recordings_dir'], exist_ok=True)
        
    def start(self):
        """启动系统"""
        print("=" * 70)
        print("双向语音通信系统")
        print("=" * 70)
        print(f"\n配置:")
        print(f"  SIP服务器: {CONFIG['server']}:{CONFIG['port']}")
        print(f"  主叫号码: {CONFIG['caller_number']}")
        print(f"  通信模式: {self.mode.value}")
        print(f"  音频目录: {CONFIG['audio_dir']}")
        print(f"  录音目录: {CONFIG['recordings_dir']}")
        print(f"  API监听: {CONFIG['api_host']}:{CONFIG['api_port']}")
        print("=" * 70 + "\n")
        
        try:
            # 创建库实例
            self.lib = pj.Lib()
            
            # 配置媒体
            media_cfg = pj.MediaConfig()
            media_cfg.enable_ice = False
            media_cfg.no_vad = True
            media_cfg.ec_tail_len = 200
            media_cfg.clock_rate = 8000
            media_cfg.channel_count = 1
            
            # 初始化
            self.lib.init(
                log_cfg=pj.LogConfig(level=CONFIG['log_level'], callback=None),
                media_cfg=media_cfg
            )
            
            # 创建UDP传输
            self.transport = self.lib.create_transport(pj.TransportType.UDP, pj.TransportConfig(0))
            print(f"✓ 传输创建: {self.transport.info().host}:{self.transport.info().port}")
            
            # 启动库
            self.lib.start()
            
            # 设置音频设备
            if self.mode == VoiceMode.MICROPHONE:
                # 麦克风模式: 尝试使用真实音频设备
                try:
                    # 检查是否有音频设备
                    import subprocess
                    result = subprocess.run(['which', 'aplay'], 
                                          capture_output=True, 
                                          timeout=1)
                    
                    if result.returncode == 0:
                        # 有音频工具，使用真实设备
                        print("✓ 音频设备: 系统默认设备 (麦克风 + 扬声器)")
                    else:
                        # 没有音频设备，降级到null设备
                        print("⚠ 警告: 未检测到音频设备，降级到null设备")
                        print("  麦克风模式需要音频硬件才能正常工作")
                        self.lib.set_null_snd_dev()
                        print("✓ 音频设备: null设备 (服务器模式)")
                except Exception as e:
                    # 出错时使用null设备
                    print(f"⚠ 音频设备检测失败: {e}")
                    print("  降级到null设备")
                    try:
                        self.lib.set_null_snd_dev()
                        print("✓ 音频设备: null设备 (服务器模式)")
                    except:
                        pass
            else:
                # 其他模式: 使用null设备
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
            
            print("=" * 70)
            print("系统已启动!")
            print("=" * 70)
            
            return True
            
        except pj.Error as e:
            print(f"\n✗ 启动失败: {e}")
            return False
    
    def make_call(self, phone_number):
        """发起呼叫"""
        self.command_queue.put(('call', phone_number))
        try:
            result = self.result_queue.get(timeout=5)
            return result
        except queue.Empty:
            print("✗ 呼叫请求超时")
            return None
    
    def _make_call_internal(self, phone_number):
        """内部呼叫方法"""
        if not self.acc:
            print("✗ 账户未初始化")
            return None
        
        full_number = f"{CONFIG['prefix']}{phone_number}"
        sip_uri = f"sip:{full_number}@{CONFIG['server']}:{CONFIG['port']}"
        
        print(f"\n发起呼叫:")
        print(f"  目标号码: {phone_number}")
        print(f"  完整号码: {full_number}")
        print(f"  SIP URI: {sip_uri}")
        print(f"  通信模式: {self.mode.value}")
        
        try:
            self.current_callback = TwoWayVoiceCallback(voice_system=self, mode=self.mode)
            self.current_call = self.acc.make_call(sip_uri, cb=self.current_callback)
            
            print("✓ 呼叫已发起")
            return self.current_call
            
        except pj.Error as e:
            print(f"✗ 呼叫失败: {e}")
            return None
    
    def on_call_connected(self, callback):
        """呼叫接通后的处理"""
        print("\n[系统] 呼叫已接通，初始化通信...")
        
        time.sleep(1)  # 等待媒体稳定
        
        # 开始录音
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        record_file = os.path.join(CONFIG['recordings_dir'], f"call_{timestamp}.wav")
        callback.start_recording(record_file)
        
        # 根据模式执行不同的初始化
        if self.mode == VoiceMode.MICROPHONE:
            print("[系统] 麦克风模式: 现在可以直接通话")
            
        elif self.mode == VoiceMode.AUDIO_QUEUE:
            print("[系统] 音频队列模式: 可以通过API添加音频到队列")
            # 自动播放欢迎语（如果存在）
            welcome_file = os.path.join(CONFIG['audio_dir'], "welcome.wav")
            if os.path.exists(welcome_file):
                callback.add_to_queue("welcome.wav")
                callback.start_auto_play()
            
        elif self.mode == VoiceMode.HYBRID:
            print("[系统] 混合模式: 队列播放 + 语音录制")
            callback.start_auto_play()
        
        print("[系统] 初始化完成\n")
    
    def hangup_current_call(self):
        """挂断当前呼叫"""
        self.command_queue.put(('hangup', None))
        try:
            result = self.result_queue.get(timeout=2)
            return result
        except queue.Empty:
            return False
    
    def _hangup_internal(self):
        """内部挂断方法"""
        if self.current_call:
            try:
                self.current_call.hangup()
                print("✓ 呼叫已挂断")
                return True
            except:
                return False
        return False
    
    def add_audio_to_queue(self, filename):
        """添加音频到播放队列"""
        if self.current_callback:
            return self.current_callback.add_to_queue(filename)
        return False
    
    def play_audio_now(self, filename):
        """立即播放音频（不使用队列）"""
        if self.current_callback:
            audio_path = os.path.join(CONFIG['audio_dir'], filename)
            return self.current_callback.play_audio_file(audio_path)
        return False
    
    def get_status(self):
        """获取系统状态"""
        status = {
            'has_active_call': self.current_call is not None,
            'mode': self.mode.value,
            'call_connected': False,
            'queue_size': 0
        }
        
        if self.current_callback:
            status['call_connected'] = self.current_callback.call_connected
            status['queue_size'] = self.current_callback.audio_queue.get_queue_size()
        
        return status
    
    def switch_mode(self, new_mode):
        """切换通信模式（仅在无活动呼叫时）"""
        if self.current_call:
            print("✗ 有活动呼叫，无法切换模式")
            return False
        
        self.mode = new_mode
        print(f"✓ 已切换到模式: {new_mode.value}")
        return True
    
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

class VoiceAPIHandler(BaseHTTPRequestHandler):
    """HTTP API处理器"""
    
    voice_system = None  # 由主程序设置
    
    def do_POST(self):
        """处理POST请求"""
        path = urlparse(self.path).path
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(body) if body else {}
        except:
            data = {}
        
        # 路由处理
        if path == '/api/call':
            self.handle_make_call(data)
        elif path == '/api/hangup':
            self.handle_hangup(data)
        elif path == '/api/add_audio':
            self.handle_add_audio(data)
        elif path == '/api/play_now':
            self.handle_play_now(data)
        elif path == '/api/status':
            self.handle_status(data)
        elif path == '/api/switch_mode':
            self.handle_switch_mode(data)
        else:
            self.send_error_response("未知的API路径")
    
    def do_GET(self):
        """处理GET请求"""
        if self.path == '/':
            self.send_html_response()
        else:
            self.send_error_response("未找到")
    
    def handle_make_call(self, data):
        """处理拨号请求"""
        phone_number = data.get('phone_number', '')
        
        if not phone_number:
            self.send_error_response("缺少phone_number参数")
            return
        
        call = self.voice_system.make_call(phone_number)
        
        if call:
            self.send_json_response({
                'success': True,
                'message': '呼叫已发起',
                'phone_number': phone_number,
                'mode': self.voice_system.mode.value
            })
        else:
            self.send_error_response("呼叫失败")
    
    def handle_hangup(self, data):
        """处理挂断请求"""
        result = self.voice_system.hangup_current_call()
        
        if result:
            self.send_json_response({
                'success': True,
                'message': '呼叫已挂断'
            })
        else:
            self.send_error_response("没有活动的呼叫")
    
    def handle_add_audio(self, data):
        """添加音频到队列"""
        filename = data.get('filename', '')
        
        if not filename:
            self.send_error_response("缺少filename参数")
            return
        
        result = self.voice_system.add_audio_to_queue(filename)
        
        if result:
            status = self.voice_system.get_status()
            self.send_json_response({
                'success': True,
                'message': f'已添加到队列: {filename}',
                'queue_size': status['queue_size']
            })
        else:
            self.send_error_response("添加失败")
    
    def handle_play_now(self, data):
        """立即播放音频"""
        filename = data.get('filename', '')
        
        if not filename:
            self.send_error_response("缺少filename参数")
            return
        
        result = self.voice_system.play_audio_now(filename)
        
        if result:
            self.send_json_response({
                'success': True,
                'message': f'正在播放: {filename}'
            })
        else:
            self.send_error_response("播放失败")
    
    def handle_status(self, data):
        """获取系统状态"""
        status = self.voice_system.get_status()
        self.send_json_response({
            'success': True,
            **status
        })
    
    def handle_switch_mode(self, data):
        """切换通信模式"""
        mode_str = data.get('mode', '')
        
        try:
            new_mode = VoiceMode(mode_str)
            result = self.voice_system.switch_mode(new_mode)
            
            if result:
                self.send_json_response({
                    'success': True,
                    'message': f'已切换到模式: {new_mode.value}',
                    'mode': new_mode.value
                })
            else:
                self.send_error_response("切换失败（可能有活动呼叫）")
        except ValueError:
            self.send_error_response(f"无效的模式: {mode_str}")
    
    def send_json_response(self, data):
        """发送JSON响应"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def send_error_response(self, message):
        """发送错误响应"""
        self.send_response(400)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({
            'success': False,
            'error': message
        }, ensure_ascii=False).encode('utf-8'))
    
    def send_html_response(self):
        """发送HTML控制页面"""
        html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>双向语音通信控制面板</title>
    <style>
        body { 
            font-family: 'Segoe UI', Arial, sans-serif; 
            max-width: 800px; 
            margin: 30px auto; 
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 { 
            color: #333; 
            margin-top: 0;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }
        .mode-selector {
            background: #e8f5e9;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }
        .mode-selector label {
            margin-right: 15px;
            font-weight: bold;
        }
        .control-section {
            margin: 20px 0;
            padding: 15px;
            background: #f9f9f9;
            border-radius: 5px;
        }
        .control-section h3 {
            margin-top: 0;
            color: #555;
        }
        input[type="text"] { 
            padding: 10px; 
            margin: 5px; 
            font-size: 16px;
            border: 1px solid #ddd;
            border-radius: 4px;
            width: 300px;
        }
        button { 
            padding: 10px 20px; 
            margin: 5px; 
            font-size: 16px;
            background: #4CAF50; 
            color: white; 
            border: none; 
            cursor: pointer;
            border-radius: 4px;
            transition: background 0.3s;
        }
        button:hover { background: #45a049; }
        button:disabled { 
            background: #ccc; 
            cursor: not-allowed; 
        }
        .btn-hangup { background: #f44336; }
        .btn-hangup:hover { background: #da190b; }
        .btn-secondary { background: #2196F3; }
        .btn-secondary:hover { background: #0b7dda; }
        #status {
            background: #fff3cd;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
            border-left: 4px solid #ffc107;
            font-family: monospace;
        }
        #log { 
            background: #263238; 
            color: #aed581;
            padding: 15px; 
            margin-top: 20px; 
            height: 300px; 
            overflow-y: auto; 
            font-family: 'Courier New', monospace;
            border-radius: 5px;
            font-size: 14px;
        }
        .status-item {
            display: inline-block;
            margin-right: 20px;
            padding: 5px 10px;
            background: white;
            border-radius: 3px;
        }
        .mode-badge {
            display: inline-block;
            padding: 5px 10px;
            background: #4CAF50;
            color: white;
            border-radius: 3px;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎙️ 双向语音通信控制面板</h1>
        
        <div class="mode-selector">
            <label>通信模式:</label>
            <select id="mode" onchange="switchMode()">
                <option value="audio_queue">音频队列模式 (预录音频)</option>
                <option value="microphone">麦克风模式 (实时通话)</option>
                <option value="hybrid">混合模式 (队列+录制)</option>
            </select>
            <span class="mode-badge" id="current-mode">audio_queue</span>
        </div>
        
        <div id="status">
            <strong>系统状态:</strong><br>
            <span class="status-item">呼叫状态: <span id="call-status">空闲</span></span>
            <span class="status-item">队列长度: <span id="queue-size">0</span></span>
        </div>
        
        <div class="control-section">
            <h3>📞 呼叫控制</h3>
            <input type="text" id="phone" placeholder="输入号码 (例如: 82121065486)">
            <button onclick="makeCall()">拨号</button>
            <button class="btn-hangup" onclick="hangup()">挂断</button>
        </div>
        
        <div class="control-section">
            <h3>🎵 音频控制 (队列模式)</h3>
            <input type="text" id="audio-file" placeholder="音频文件名 (例如: welcome.wav)">
            <button class="btn-secondary" onclick="addToQueue()">添加到队列</button>
            <button class="btn-secondary" onclick="playNow()">立即播放</button>
        </div>
        
        <button onclick="refreshStatus()" style="width: 100%; margin-top: 10px;">🔄 刷新状态</button>
        
        <div id="log">系统就绪...\n等待操作...</div>
    </div>
    
    <script>
        function log(msg, type='info') {
            const logEl = document.getElementById('log');
            const time = new Date().toLocaleTimeString();
            const prefix = type === 'error' ? '✗' : type === 'success' ? '✓' : '•';
            logEl.innerHTML += `[${time}] ${prefix} ${msg}\n`;
            logEl.scrollTop = logEl.scrollHeight;
        }
        
        function updateStatus(data) {
            document.getElementById('call-status').textContent = 
                data.has_active_call ? (data.call_connected ? '通话中' : '呼叫中') : '空闲';
            document.getElementById('queue-size').textContent = data.queue_size || 0;
            document.getElementById('current-mode').textContent = data.mode || 'unknown';
            document.getElementById('mode').value = data.mode || 'audio_queue';
        }
        
        function makeCall() {
            const phone = document.getElementById('phone').value.trim();
            if (!phone) {
                alert('请输入号码');
                return;
            }
            
            log(`正在拨打: ${phone}`);
            
            fetch('/api/call', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({phone_number: phone})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    log(`呼叫已发起 (模式: ${data.mode})`, 'success');
                    setTimeout(refreshStatus, 1000);
                } else {
                    log(`呼叫失败: ${data.error}`, 'error');
                }
            })
            .catch(e => log(`请求失败: ${e}`, 'error'));
        }
        
        function hangup() {
            log('正在挂断...');
            
            fetch('/api/hangup', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    log('呼叫已挂断', 'success');
                    setTimeout(refreshStatus, 500);
                } else {
                    log(`挂断失败: ${data.error}`, 'error');
                }
            })
            .catch(e => log(`请求失败: ${e}`, 'error'));
        }
        
        function addToQueue() {
            const filename = document.getElementById('audio-file').value.trim();
            if (!filename) {
                alert('请输入音频文件名');
                return;
            }
            
            log(`添加到队列: ${filename}`);
            
            fetch('/api/add_audio', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({filename: filename})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    log(`已添加: ${filename} (队列: ${data.queue_size})`, 'success');
                    document.getElementById('queue-size').textContent = data.queue_size;
                } else {
                    log(`添加失败: ${data.error}`, 'error');
                }
            })
            .catch(e => log(`请求失败: ${e}`, 'error'));
        }
        
        function playNow() {
            const filename = document.getElementById('audio-file').value.trim();
            if (!filename) {
                alert('请输入音频文件名');
                return;
            }
            
            log(`立即播放: ${filename}`);
            
            fetch('/api/play_now', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({filename: filename})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    log(`正在播放: ${filename}`, 'success');
                } else {
                    log(`播放失败: ${data.error}`, 'error');
                }
            })
            .catch(e => log(`请求失败: ${e}`, 'error'));
        }
        
        function switchMode() {
            const mode = document.getElementById('mode').value;
            
            log(`切换模式到: ${mode}`);
            
            fetch('/api/switch_mode', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({mode: mode})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    log(`已切换到: ${data.mode}`, 'success');
                    document.getElementById('current-mode').textContent = data.mode;
                } else {
                    log(`切换失败: ${data.error}`, 'error');
                }
            })
            .catch(e => log(`请求失败: ${e}`, 'error'));
        }
        
        function refreshStatus() {
            fetch('/api/status', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    updateStatus(data);
                    log('状态已刷新', 'info');
                }
            })
            .catch(e => log(`刷新失败: ${e}`, 'error'));
        }
        
        // 自动刷新状态
        setInterval(refreshStatus, 3000);
        refreshStatus();
    </script>
</body>
</html>
        """
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def log_message(self, format, *args):
        """禁用默认日志"""
        pass


def run_api_server(voice_system):
    """运行API服务器"""
    VoiceAPIHandler.voice_system = voice_system
    
    server = HTTPServer((CONFIG['api_host'], CONFIG['api_port']), VoiceAPIHandler)
    print(f"✓ API服务器启动: http://localhost:{CONFIG['api_port']}")
    print(f"  控制面板: http://localhost:{CONFIG['api_port']}/")
    print()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


# ==================== 主程序 ====================

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='双向语音通信系统')
    parser.add_argument('--mode', 
                        choices=['microphone', 'audio_queue', 'hybrid'],
                        default=CONFIG['default_mode'].lower(),
                        help='通信模式')
    
    args = parser.parse_args()
    
    # 解析模式
    mode = VoiceMode(args.mode)
    
    print("\n启动双向语音通信系统...\n")
    
    # 创建系统
    voice_system = TwoWayVoiceSystem(mode=mode)
    
    if not voice_system.start():
        print("系统启动失败")
        sys.exit(1)
    
    # 在新线程中启动API服务器
    api_thread = threading.Thread(target=run_api_server, args=(voice_system,), daemon=True)
    api_thread.start()
    
    print("\n" + "="*70)
    print("使用说明:")
    print("  1. 访问控制面板: http://localhost:8088")
    print("  2. 或使用API接口控制")
    print("  3. 音频文件放在: " + CONFIG['audio_dir'])
    print("  4. 录音保存在: " + CONFIG['recordings_dir'])
    print("="*70)
    print("\n按 Ctrl+C 停止系统\n")
    
    try:
        while True:
            # 处理命令队列
            try:
                cmd, data = voice_system.command_queue.get(timeout=0.1)
                
                if cmd == 'call':
                    result = voice_system._make_call_internal(data)
                    voice_system.result_queue.put(result)
                    
                elif cmd == 'hangup':
                    result = voice_system._hangup_internal()
                    voice_system.result_queue.put(result)
                    
                elif cmd == 'call_connected':
                    voice_system.on_call_connected(data)
                    
            except queue.Empty:
                pass
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n\n正在停止系统...")
        voice_system.stop()


if __name__ == "__main__":
    main()

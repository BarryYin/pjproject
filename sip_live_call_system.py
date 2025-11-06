#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIP双向实时通话系统 - 印度尼西亚线路
功能:
1. 支持双向实时语音通话（你说话对方能听见，对方说话你能听见）
2. 自动检测并使用真实音频设备（麦克风+扬声器）
3. HTTP API控制（拨号、挂断、静音等）
4. Web控制界面
"""

import sys
import time
import pjsua as pj
import threading
import os
import json
import queue
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# 配置
CONFIG = {
    'server': '147.139.205.88',
    'port': 5060,
    'caller_number': '6281479242434',
    'prefix': '13462',
    'log_level': 3,
    
    # 音频配置
    'use_real_audio': True,  # 使用真实音频设备
    'recordings_dir': '/home/henry/pjproject/recordings',
    
    # HTTP API配置
    'api_host': '0.0.0.0',
    'api_port': 8089
}

LOG_LEVEL = CONFIG['log_level']


class LiveCallCallback(pj.CallCallback):
    """实时通话回调"""
    
    def __init__(self, call=None, call_system=None):
        pj.CallCallback.__init__(self, call)
        self.call_system = call_system
        self.call_connected = False
        self.call_ended = False
        self.start_time = time.time()
        self.connect_time = None
        self.is_muted = False
        self.is_recording = False
        self.wav_recorder = None
        self.recorder_id = None
        
    def on_state(self):
        """呼叫状态变化"""
        info = self.call.info()
        elapsed = time.time() - self.start_time
        
        print(f"\n[{elapsed:.1f}s] 呼叫状态: {info.state_text}")
        print(f"  远程: {info.remote_uri}")
        print(f"  响应: {info.last_code} ({info.last_reason})")
        
        if info.state == pj.CallState.CALLING:
            print("  >>> 正在发起呼叫...")
            
        elif info.state == pj.CallState.EARLY:
            if info.last_code == 180:
                print("  >>> 对方振铃中...")
            elif info.last_code == 183:
                print("  >>> 会话进行中...")
                
        elif info.state == pj.CallState.CONFIRMED:
            self.call_connected = True
            self.connect_time = time.time()
            print("  >>> ✓ 呼叫已接通！")
            print("  >>> 现在可以开始双向通话了")
            print("  >>> 你说话对方能听见，对方说话你也能听见")
            
        elif info.state == pj.CallState.DISCONNECTED:
            self.call_ended = True
            duration = time.time() - self.start_time
            print(f"  >>> 呼叫结束 (总时长: {duration:.1f}秒)")
            
            if info.last_code == 200:
                print("  原因: 正常挂断")
            elif info.last_code == 486:
                print("  原因: 用户忙")
            elif info.last_code == 487:
                print("  原因: 请求已取消")
            elif info.last_code == 480:
                print("  原因: 暂时无法接通")
            else:
                print(f"  原因: {info.last_reason}")
                
            if self.call_connected and self.connect_time:
                talk_time = time.time() - self.connect_time
                print(f"  通话时长: {talk_time:.1f}秒")
            
            self.cleanup()
            
    def on_media_state(self):
        """媒体状态变化 - 建立双向音频连接"""
        info = self.call.info()
        if info.media_state == pj.MediaState.ACTIVE:
            call_slot = info.conf_slot
            
            # 双向连接音频会议桥
            # 1. 对方的声音 -> 你的扬声器（你能听到对方）
            pj.Lib.instance().conf_connect(call_slot, 0)
            # 2. 你的麦克风 -> 对方（对方能听到你）
            pj.Lib.instance().conf_connect(0, call_slot)
            
            print("  [媒体] ✓ 双向音频通道已激活")
            print("  [媒体]   对方声音 -> 你的扬声器")
            print("  [媒体]   你的麦克风 -> 对方")
    
    def toggle_mute(self):
        """切换静音状态"""
        try:
            info = self.call.info()
            if info.state != pj.CallState.CONFIRMED:
                return False, "呼叫未接通"
            
            call_slot = info.conf_slot
            
            if self.is_muted:
                # 取消静音：重新连接麦克风到对方
                pj.Lib.instance().conf_connect(0, call_slot)
                self.is_muted = False
                print("  [静音] 已取消静音 - 对方现在能听到你")
                return True, "已取消静音"
            else:
                # 静音：断开麦克风到对方的连接
                pj.Lib.instance().conf_disconnect(0, call_slot)
                self.is_muted = True
                print("  [静音] 已静音 - 对方听不到你的声音")
                return True, "已静音"
                
        except Exception as e:
            print(f"  [静音] 操作失败: {e}")
            return False, str(e)
    
    def start_recording(self, record_file):
        """开始录音"""
        try:
            info = self.call.info()
            if info.state != pj.CallState.CONFIRMED:
                return False, "呼叫未接通"
            
            if self.is_recording:
                return False, "已在录音中"
            
            # 创建录音器
            self.wav_recorder = pj.Lib.instance().create_recorder(record_file)
            self.recorder_id = pj.Lib.instance().recorder_get_slot(self.wav_recorder)
            
            # 连接音频源到录音器
            # 录制对方的声音
            pj.Lib.instance().conf_connect(info.conf_slot, self.recorder_id)
            # 录制自己的声音
            pj.Lib.instance().conf_connect(0, self.recorder_id)
            
            self.is_recording = True
            print(f"  [录音] ✓ 开始录制: {os.path.basename(record_file)}")
            return True, "录音已开始"
            
        except Exception as e:
            print(f"  [录音] 失败: {e}")
            return False, str(e)
    
    def stop_recording(self):
        """停止录音"""
        if not self.is_recording:
            return False, "未在录音"
            
        try:
            info = self.call.info()
            pj.Lib.instance().conf_disconnect(info.conf_slot, self.recorder_id)
            pj.Lib.instance().conf_disconnect(0, self.recorder_id)
            self.wav_recorder = None
            self.is_recording = False
            print("  [录音] 已停止")
            return True, "录音已停止"
        except Exception as e:
            print(f"  [录音] 停止失败: {e}")
            return False, str(e)
    
    def cleanup(self):
        """清理资源"""
        if self.is_recording:
            try:
                self.stop_recording()
            except:
                pass


class LiveCallSystem:
    """双向实时通话系统核心"""
    
    def __init__(self):
        self.lib = None
        self.acc = None
        self.transport = None
        self.current_call = None
        self.current_callback = None
        
        # 命令队列 - 线程安全
        self.command_queue = queue.Queue()
        self.result_queue = queue.Queue()
        
        # 创建录音目录
        os.makedirs(CONFIG['recordings_dir'], exist_ok=True)
        
    def check_system_audio(self):
        """检查系统音频设备"""
        print("\n" + "=" * 70)
        print("系统音频检测")
        print("=" * 70)
        
        has_audio = False
        
        # 检查PulseAudio输出
        try:
            result = subprocess.run(['pactl', 'list', 'sinks', 'short'], 
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0 and result.stdout.strip():
                sinks = [s for s in result.stdout.strip().split('\n') if s]
                print(f"\n[PulseAudio 输出设备] 共 {len(sinks)} 个:")
                for sink in sinks:
                    parts = sink.split('\t')
                    if len(parts) >= 2:
                        dev_name = parts[1]
                        print(f"  ✓ {dev_name}")
                        if 'null' not in dev_name.lower():
                            has_audio = True
        except Exception:
            pass
        
        # 检查PulseAudio输入
        try:
            result = subprocess.run(['pactl', 'list', 'sources', 'short'], 
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0 and result.stdout.strip():
                sources = [s for s in result.stdout.strip().split('\n') 
                          if s and 'monitor' not in s.lower()]
                print(f"\n[PulseAudio 输入设备] 共 {len(sources)} 个:")
                for source in sources:
                    parts = source.split('\t')
                    if len(parts) >= 2:
                        dev_name = parts[1]
                        print(f"  ✓ {dev_name}")
                        if 'null' not in dev_name.lower():
                            has_audio = True
        except Exception:
            pass
        
        print()
        return has_audio
    
    def list_audio_devices(self):
        """列出PJSUA音频设备"""
        print("=" * 70)
        print("PJSUA 音频设备")
        print("=" * 70)
        
        try:
            if hasattr(self.lib, 'enum_snd_dev'):
                devices = self.lib.enum_snd_dev()
                
                if not devices:
                    print("\n⚠ 未检测到音频设备")
                    return None
                
                print(f"\n✓ 检测到 {len(devices)} 个音频设备:\n")
                
                for i, dev in enumerate(devices):
                    print(f"  [{i}] {dev.name}")
                    # 检查设备是否有input_count和output_count属性
                    try:
                        if hasattr(dev, 'input_count') and hasattr(dev, 'output_count'):
                            print(f"      输入: {dev.input_count} | 输出: {dev.output_count}")
                    except:
                        pass
                    if 'null' in dev.name.lower():
                        print("      ⚠ 虚拟设备")
                    print()
                
                return devices
            else:
                print("\n✓ 使用系统默认音频设备")
                return None
                
        except Exception as e:
            print(f"\n⚠ 音频设备检测失败: {e}")
            return None
    
    def start(self):
        """启动通话系统"""
        print("=" * 70)
        print("SIP 双向实时通话系统 - 印度尼西亚线路")
        print("=" * 70)
        print(f"\n配置:")
        print(f"  SIP服务器: {CONFIG['server']}:{CONFIG['port']}")
        print(f"  主叫号码: {CONFIG['caller_number']}")
        print(f"  被叫前缀: {CONFIG['prefix']}")
        print(f"  音频模式: {'真实音频设备' if CONFIG['use_real_audio'] else 'null设备'}")
        print(f"  录音目录: {CONFIG['recordings_dir']}")
        print(f"  API监听: {CONFIG['api_host']}:{CONFIG['api_port']}")
        print("=" * 70 + "\n")
        
        # 检查系统音频
        has_audio = self.check_system_audio()
        if not has_audio and CONFIG['use_real_audio']:
            print("⚠ 警告: 未检测到真实音频设备，可能无法正常通话")
            print("⚠ 如果是远程服务器，需要配置音频转发或使用本地环境\n")
        
        try:
            # 创建库实例
            self.lib = pj.Lib()
            
            # 配置媒体
            media_cfg = pj.MediaConfig()
            media_cfg.enable_ice = False
            media_cfg.no_vad = True
            media_cfg.ec_tail_len = 200
            media_cfg.clock_rate = 8000
            media_cfg.snd_auto_close_time = -1  # 不自动关闭音频设备
            
            # 初始化
            self.lib.init(
                log_cfg=pj.LogConfig(level=LOG_LEVEL, callback=None),
                media_cfg=media_cfg
            )
            
            # 创建UDP传输
            self.transport = self.lib.create_transport(pj.TransportType.UDP, pj.TransportConfig(0))
            print(f"✓ 传输创建: {self.transport.info().host}:{self.transport.info().port}")
            
            # 启动库
            self.lib.start()
            
            # 配置音频设备
            if CONFIG['use_real_audio']:
                devices = self.list_audio_devices()
                
                # 查找真实音频设备
                capture_dev = -1
                playback_dev = -1
                
                if devices:
                    for i, dev in enumerate(devices):
                        try:
                            # 尝试检查是否有真实音频设备
                            has_io = True
                            if hasattr(dev, 'input_count') and hasattr(dev, 'output_count'):
                                has_io = dev.input_count > 0 and dev.output_count > 0
                            
                            if 'null' not in dev.name.lower() and has_io:
                                capture_dev = i
                                playback_dev = i
                                break
                        except:
                            continue
                
                try:
                    self.lib.set_snd_dev(capture_dev, playback_dev)
                    if capture_dev == -1:
                        print("✓ 音频设备: 系统默认\n")
                    else:
                        print(f"✓ 音频设备: [{capture_dev}] {devices[capture_dev].name}\n")
                except Exception as e:
                    print(f"⚠ 音频设备配置失败: {e}")
                    print("  尝试使用默认设备\n")
            else:
                # 使用null设备（服务器模式）
                try:
                    self.lib.set_null_snd_dev()
                    print("✓ 音频设备: null设备（无实际声音）\n")
                except:
                    pass
            
            # 创建账户
            acc_cfg = pj.AccountConfig()
            acc_cfg.id = f"sip:{CONFIG['caller_number']}@{CONFIG['server']}"
            acc_cfg.reg_uri = ""
            
            self.acc = self.lib.create_account(acc_cfg)
            print("✓ 账户已创建")
            
            print("\n" + "=" * 70)
            print("✓ 双向实时通话系统已启动!")
            print("=" * 70 + "\n")
            
            return True
            
        except pj.Error as e:
            print(f"\n✗ 启动失败: {e}")
            return False
    
    def make_call(self, phone_number):
        """发起呼叫（通过队列，线程安全）"""
        self.command_queue.put(('call', phone_number))
        try:
            result = self.result_queue.get(timeout=5)
            return result
        except queue.Empty:
            print("✗ 呼叫请求超时")
            return {'success': False, 'error': '超时'}
    
    def _make_call_internal(self, phone_number):
        """内部呼叫方法"""
        if not self.acc:
            print("✗ 账户未初始化")
            return None
        
        if self.current_call:
            try:
                # 检查当前呼叫状态
                info = self.current_call.info()
                if info.state != pj.CallState.DISCONNECTED:
                    print("✗ 已有活动呼叫")
                    return None
            except:
                pass
        
        # 构造完整号码
        full_number = f"{CONFIG['prefix']}{phone_number}"
        sip_uri = f"sip:{full_number}@{CONFIG['server']}:{CONFIG['port']}"
        
        print(f"\n发起呼叫:")
        print(f"  目标号码: {phone_number}")
        print(f"  完整号码: {full_number}")
        print(f"  SIP URI: {sip_uri}")
        
        try:
            self.current_callback = LiveCallCallback(call_system=self)
            self.current_call = self.acc.make_call(sip_uri, cb=self.current_callback)
            
            print("✓ 呼叫已发起")
            return self.current_call
            
        except pj.Error as e:
            print(f"✗ 呼叫失败: {e}")
            return None
    
    def hangup(self):
        """挂断呼叫（通过队列，线程安全）"""
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
                self.current_call = None
                self.current_callback = None
                print("✓ 呼叫已挂断")
                return True
            except Exception as e:
                print(f"✗ 挂断失败: {e}")
                return False
        return False
    
    def toggle_mute(self):
        """切换静音（通过队列，线程安全）"""
        self.command_queue.put(('mute', None))
        try:
            result = self.result_queue.get(timeout=2)
            return result
        except queue.Empty:
            return False, "超时"
    
    def _toggle_mute_internal(self):
        """内部静音切换"""
        if self.current_callback:
            return self.current_callback.toggle_mute()
        return False, "无活动呼叫"
    
    def start_recording(self):
        """开始录音（通过队列，线程安全）"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        record_file = os.path.join(CONFIG['recordings_dir'], f"call_{timestamp}.wav")
        self.command_queue.put(('record_start', record_file))
        try:
            result = self.result_queue.get(timeout=2)
            return result
        except queue.Empty:
            return False, "超时"
    
    def _start_recording_internal(self, record_file):
        """内部录音开始"""
        if self.current_callback:
            return self.current_callback.start_recording(record_file)
        return False, "无活动呼叫"
    
    def stop_recording(self):
        """停止录音（通过队列，线程安全）"""
        self.command_queue.put(('record_stop', None))
        try:
            result = self.result_queue.get(timeout=2)
            return result
        except queue.Empty:
            return False, "超时"
    
    def _stop_recording_internal(self):
        """内部录音停止"""
        if self.current_callback:
            return self.current_callback.stop_recording()
        return False, "无活动呼叫"
    
    def get_call_status(self):
        """获取呼叫状态（线程安全 - 使用缓存，不直接访问PJSUA对象）"""
        if not self.current_callback:
            return None
        
        try:
            # 不访问PJSUA对象，只返回callback中的状态信息
            return {
                'connected': self.current_callback.call_connected,
                'ended': self.current_callback.call_ended,
                'duration': time.time() - self.current_callback.start_time,
                'is_muted': self.current_callback.is_muted,
                'is_recording': self.current_callback.is_recording
            }
        except:
            return None
    
    def stop(self):
        """停止系统"""
        if self.current_call:
            self.hangup()
            time.sleep(1)
            
        if self.lib:
            try:
                self.lib.destroy()
            except:
                pass
        
        print("\n双向通话系统已停止")


class APIHandler(BaseHTTPRequestHandler):
    """HTTP API处理器"""
    
    call_system = None
    
    def do_POST(self):
        """处理POST请求"""
        path = urlparse(self.path).path
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(body) if body else {}
        except:
            data = {}
        
        if path == '/api/call':
            self.handle_make_call(data)
        elif path == '/api/hangup':
            self.handle_hangup(data)
        elif path == '/api/mute':
            self.handle_mute(data)
        elif path == '/api/record/start':
            self.handle_record_start(data)
        elif path == '/api/record/stop':
            self.handle_record_stop(data)
        elif path == '/api/status':
            self.handle_status(data)
        else:
            self.send_error_response("未知的API路径")
    
    def do_GET(self):
        """处理GET请求"""
        if self.path == '/' or self.path == '/index.html':
            self.send_html_response()
        else:
            self.send_error_response("未找到", 404)
    
    def handle_make_call(self, data):
        """拨号"""
        phone_number = data.get('phone_number', '')
        
        if not phone_number:
            self.send_error_response("缺少phone_number参数")
            return
        
        result = self.call_system.make_call(phone_number)
        
        if isinstance(result, dict) and result.get('success'):
            self.send_json_response({
                'success': True,
                'message': '呼叫已发起',
                'phone_number': phone_number
            })
        else:
            error_msg = result.get('error', '呼叫失败') if isinstance(result, dict) else '呼叫失败'
            self.send_error_response(error_msg)
    
    def handle_hangup(self, data):
        """挂断"""
        result = self.call_system.hangup()
        
        if result:
            self.send_json_response({
                'success': True,
                'message': '呼叫已挂断'
            })
        else:
            self.send_error_response("没有活动的呼叫")
    
    def handle_mute(self, data):
        """静音切换"""
        success, message = self.call_system.toggle_mute()
        
        if success:
            self.send_json_response({
                'success': True,
                'message': message
            })
        else:
            self.send_error_response(message)
    
    def handle_record_start(self, data):
        """开始录音"""
        success, message = self.call_system.start_recording()
        
        if success:
            self.send_json_response({
                'success': True,
                'message': message
            })
        else:
            self.send_error_response(message)
    
    def handle_record_stop(self, data):
        """停止录音"""
        success, message = self.call_system.stop_recording()
        
        if success:
            self.send_json_response({
                'success': True,
                'message': message
            })
        else:
            self.send_error_response(message)
    
    def handle_status(self, data):
        """获取状态"""
        status = self.call_system.get_call_status()
        
        self.send_json_response({
            'success': True,
            'status': status
        })
    
    def send_json_response(self, data):
        """发送JSON响应"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def send_error_response(self, message, code=400):
        """发送错误响应"""
        self.send_response(code)
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
    <title>双向通话控制面板</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Arial, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 600px;
            width: 100%;
            padding: 40px;
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 28px;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }
        .call-section {
            margin-bottom: 30px;
        }
        .input-group {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }
        input {
            flex: 1;
            padding: 12px 15px;
            font-size: 16px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            transition: all 0.3s;
        }
        input:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            padding: 12px 25px;
            font-size: 16px;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s;
            font-weight: 600;
            color: white;
        }
        .btn-call {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            flex: 1;
        }
        .btn-call:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4); }
        .btn-hangup {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            flex: 1;
        }
        .btn-hangup:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(245, 87, 108, 0.4); }
        .btn-mute {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }
        .btn-mute:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(79, 172, 254, 0.4); }
        .btn-record {
            background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        }
        .btn-record:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(67, 233, 123, 0.4); }
        .btn-record.recording {
            background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
            animation: pulse 1.5s ease-in-out infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        .controls {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        .status {
            background: #f5f5f5;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .status-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #e0e0e0;
        }
        .status-item:last-child { border-bottom: none; }
        .status-label { color: #666; font-size: 14px; }
        .status-value { color: #333; font-weight: 600; font-size: 14px; }
        .status-value.connected { color: #43e97b; }
        .status-value.disconnected { color: #f5576c; }
        #log {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 15px;
            border-radius: 10px;
            height: 250px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.5;
        }
        .log-time { color: #858585; }
        .log-success { color: #43e97b; }
        .log-error { color: #f5576c; }
        .log-info { color: #4facfe; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎙️ 双向实时通话系统</h1>
        <p class="subtitle">印度尼西亚线路 | 真实音频通话</p>
        
        <div class="call-section">
            <div class="input-group">
                <input type="text" id="phone" placeholder="输入号码 (例如: 82121065486)">
                <button class="btn-call" onclick="makeCall()">📞 拨号</button>
            </div>
            <div class="input-group">
                <button class="btn-hangup" onclick="hangup()">📵 挂断</button>
            </div>
        </div>
        
        <div class="status" id="status">
            <div class="status-item">
                <span class="status-label">呼叫状态</span>
                <span class="status-value disconnected" id="call-state">未连接</span>
            </div>
            <div class="status-item">
                <span class="status-label">通话时长</span>
                <span class="status-value" id="call-duration">0秒</span>
            </div>
            <div class="status-item">
                <span class="status-label">静音状态</span>
                <span class="status-value" id="mute-state">未静音</span>
            </div>
            <div class="status-item">
                <span class="status-label">录音状态</span>
                <span class="status-value" id="record-state">未录音</span>
            </div>
        </div>
        
        <div class="controls">
            <button class="btn-mute" onclick="toggleMute()">🔇 静音/取消静音</button>
            <button class="btn-record" id="recordBtn" onclick="toggleRecord()">⏺️ 开始录音</button>
        </div>
        
        <div style="margin-top: 20px;">
            <div id="log">系统就绪，等待操作...</div>
        </div>
    </div>
    
    <script>
        let isRecording = false;
        let statusInterval = null;
        
        function log(msg, type = 'info') {
            const logEl = document.getElementById('log');
            const time = new Date().toLocaleTimeString();
            let className = 'log-info';
            if (type === 'success') className = 'log-success';
            if (type === 'error') className = 'log-error';
            
            logEl.innerHTML += `<span class="log-time">[${time}]</span> <span class="${className}">${msg}</span><br>`;
            logEl.scrollTop = logEl.scrollHeight;
        }
        
        function updateStatus() {
            fetch('/api/status', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            })
            .then(r => r.json())
            .then(data => {
                if (data.success && data.status) {
                    const s = data.status;
                    document.getElementById('call-state').textContent = s.connected ? '已接通' : s.state;
                    document.getElementById('call-state').className = 'status-value ' + (s.connected ? 'connected' : 'disconnected');
                    document.getElementById('call-duration').textContent = Math.floor(s.duration) + '秒';
                    document.getElementById('mute-state').textContent = s.is_muted ? '已静音' : '未静音';
                    document.getElementById('record-state').textContent = s.is_recording ? '录音中' : '未录音';
                    isRecording = s.is_recording;
                    updateRecordButton();
                } else {
                    document.getElementById('call-state').textContent = '未连接';
                    document.getElementById('call-state').className = 'status-value disconnected';
                    document.getElementById('call-duration').textContent = '0秒';
                    document.getElementById('mute-state').textContent = '未静音';
                    document.getElementById('record-state').textContent = '未录音';
                    if (statusInterval) {
                        clearInterval(statusInterval);
                        statusInterval = null;
                    }
                }
            })
            .catch(() => {});
        }
        
        function makeCall() {
            const phone = document.getElementById('phone').value.trim();
            if (!phone) {
                alert('请输入号码');
                return;
            }
            
            log(`正在拨打: ${phone}`, 'info');
            
            fetch('/api/call', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({phone_number: phone})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    log(`✓ ${data.message}`, 'success');
                    if (!statusInterval) {
                        statusInterval = setInterval(updateStatus, 1000);
                    }
                } else {
                    log(`✗ ${data.error}`, 'error');
                }
            })
            .catch(e => log(`✗ 请求失败: ${e}`, 'error'));
        }
        
        function hangup() {
            log('正在挂断...', 'info');
            
            fetch('/api/hangup', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    log(`✓ ${data.message}`, 'success');
                } else {
                    log(`✗ ${data.error}`, 'error');
                }
            })
            .catch(e => log(`✗ 请求失败: ${e}`, 'error'));
        }
        
        function toggleMute() {
            log('切换静音状态...', 'info');
            
            fetch('/api/mute', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    log(`✓ ${data.message}`, 'success');
                } else {
                    log(`✗ ${data.error}`, 'error');
                }
            })
            .catch(e => log(`✗ 请求失败: ${e}`, 'error'));
        }
        
        function toggleRecord() {
            if (isRecording) {
                log('停止录音...', 'info');
                fetch('/api/record/stop', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'}
                })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        log(`✓ ${data.message}`, 'success');
                        isRecording = false;
                        updateRecordButton();
                    } else {
                        log(`✗ ${data.error}`, 'error');
                    }
                })
                .catch(e => log(`✗ 请求失败: ${e}`, 'error'));
            } else {
                log('开始录音...', 'info');
                fetch('/api/record/start', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'}
                })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        log(`✓ ${data.message}`, 'success');
                        isRecording = true;
                        updateRecordButton();
                    } else {
                        log(`✗ ${data.error}`, 'error');
                    }
                })
                .catch(e => log(`✗ 请求失败: ${e}`, 'error'));
            }
        }
        
        function updateRecordButton() {
            const btn = document.getElementById('recordBtn');
            if (isRecording) {
                btn.textContent = '⏹️ 停止录音';
                btn.classList.add('recording');
            } else {
                btn.textContent = '⏺️ 开始录音';
                btn.classList.remove('recording');
            }
        }
        
        // 初始状态更新
        updateStatus();
        
        log('✓ 系统已启动，可以开始拨号', 'success');
        log('ℹ️ 说明：接通后你和对方可以双向对话', 'info');
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


def run_api_server(call_system):
    """运行API服务器"""
    APIHandler.call_system = call_system
    
    server = HTTPServer((CONFIG['api_host'], CONFIG['api_port']), APIHandler)
    print(f"✓ API服务器启动: http://localhost:{CONFIG['api_port']}")
    print(f"  控制面板: http://localhost:{CONFIG['api_port']}/")
    print()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


def main():
    """主函数"""
    print("\n启动双向实时通话系统...\n")
    
    # 创建通话系统
    call_system = LiveCallSystem()
    
    if not call_system.start():
        print("系统启动失败")
        sys.exit(1)
    
    # 在新线程中启动API服务器
    api_thread = threading.Thread(target=run_api_server, args=(call_system,), daemon=True)
    api_thread.start()
    
    print("按 Ctrl+C 停止系统\n")
    print("提示:")
    print("  - 接通后可以直接对话，双向实时通话")
    print("  - 使用Web界面控制：静音、录音等")
    print("  - 录音会保存双方的声音\n")
    
    try:
        # 主循环：处理命令队列（必须在PJSUA线程中）
        while True:
            try:
                # 从队列获取命令
                cmd, data = call_system.command_queue.get(timeout=0.1)
                
                if cmd == 'call':
                    result = call_system._make_call_internal(data)
                    call_system.result_queue.put({'success': result is not None, 'call': result})
                    
                elif cmd == 'hangup':
                    result = call_system._hangup_internal()
                    call_system.result_queue.put(result)
                    
                elif cmd == 'mute':
                    result = call_system._toggle_mute_internal()
                    call_system.result_queue.put(result)
                    
                elif cmd == 'record_start':
                    result = call_system._start_recording_internal(data)
                    call_system.result_queue.put(result)
                    
                elif cmd == 'record_stop':
                    result = call_system._stop_recording_internal()
                    call_system.result_queue.put(result)
                    
            except queue.Empty:
                pass
            
            time.sleep(0.05)  # 短暂休眠，保持响应
            
    except KeyboardInterrupt:
        print("\n\n正在停止系统...")
        call_system.stop()


if __name__ == "__main__":
    main()

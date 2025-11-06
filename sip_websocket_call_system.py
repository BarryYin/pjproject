#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIP双向实时通话系统 - WebSocket音频流版本
功能:
1. SIP呼叫管理（服务器端）
2. WebSocket实时音频流转发
3. 浏览器端麦克风/扬声器接入
4. 真正的双向实时通话

架构:
[客户电话] <-SIP-> [服务器PJSIP] <-WebSocket-> [浏览器] <-本地音频设备
"""

import sys
import time
import pjsua as pj
import threading
import os
import json
import queue
import subprocess
import asyncio
import websockets
import struct
import wave
from http.server import HTTPServer, BaseHTTPRequestHandler
import ssl
from urllib.parse import parse_qs, urlparse

# 配置
CONFIG = {
    'server': '147.139.205.88',
    'port': 5060,
    'caller_number': '6281479242434',
    'prefix': '13462',
    'log_level': 3,
    
    # 音频配置
    'sample_rate': 8000,  # PJSIP标准采样率
    'channels': 1,        # 单声道
    'sample_width': 2,    # 16-bit PCM
    
    # WebSocket配置
    'ws_host': '0.0.0.0',
    'ws_port': 8090,
    
    # HTTP API配置
    'api_host': '0.0.0.0',
    'api_port': 8089,
    
    # 录音配置
    'recordings_dir': '/home/henry/pjproject/recordings',
}

LOG_LEVEL = CONFIG['log_level']

# 全局音频队列
audio_from_sip_queue = queue.Queue(maxsize=100)  # SIP -> WebSocket -> 浏览器
audio_to_sip_queue = queue.Queue(maxsize=100)    # 浏览器 -> WebSocket -> SIP

# 音频捕获线程控制
audio_capture_active = False


class WebSocketCallCallback(pj.CallCallback):
    """WebSocket通话回调"""
    
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
        self.media_port = None
        
    def on_state(self):
        """呼叫状态变化"""
        info = self.call.info()
        elapsed = time.time() - self.start_time
        
        state_info = {
            'type': 'call_state',
            'state': info.state_text,
            'code': info.last_code,
            'reason': info.last_reason,
            'elapsed': elapsed
        }
        
        print(f"\n[{elapsed:.1f}s] 呼叫状态: {info.state_text}")
        print(f"  远程: {info.remote_uri}")
        print(f"  响应: {info.last_code} ({info.last_reason})")
        
        if info.state == pj.CallState.CALLING:
            print("  >>> 正在发起呼叫...")
            state_info['message'] = '正在发起呼叫'
            
        elif info.state == pj.CallState.EARLY:
            if info.last_code == 180:
                print("  >>> 对方振铃中...")
                state_info['message'] = '对方振铃中'
            elif info.last_code == 183:
                print("  >>> 会话进行中...")
                state_info['message'] = '会话进行中'
                
        elif info.state == pj.CallState.CONFIRMED:
            self.call_connected = True
            self.connect_time = time.time()
            print("  >>> ✓ 呼叫已接通！")
            
            # 打印RTP端口信息
            try:
                for i, media in enumerate(info.media):
                    if media.type == pj.MediaType.AUDIO:
                        rtp_port = media.transport.local_rtcp_port - 1
                        print(f"  >>> 🎵 RTP音频端口: {media.transport.local_name}:{rtp_port}")
                        print(f"  >>> 远程地址: {media.transport.remote_name}:{media.transport.remote_rtcp_port - 1}")
            except Exception as e:
                print(f"  >>> 获取RTP端口失败: {e}")
            
            print("  >>> WebSocket音频流已启动")
            state_info['message'] = '呼叫已接通'
            state_info['connected'] = True
            
        elif info.state == pj.CallState.DISCONNECTED:
            self.call_ended = True
            duration = time.time() - self.start_time
            print(f"  >>> 呼叫结束 (总时长: {duration:.1f}秒)")
            state_info['message'] = '呼叫结束'
            state_info['duration'] = duration
            
            self.cleanup()
        
        # 通知所有WebSocket客户端
        if self.call_system:
            self.call_system.broadcast_to_clients(state_info)
            
    def on_media_state(self):
        """媒体状态变化 - 设置音频流"""
        info = self.call.info()
        if info.media_state == pj.MediaState.ACTIVE:
            call_slot = info.conf_slot
            
            print("  [媒体] ✓ 音频通道已激活")
            print("  [媒体]   使用会议桥模式传输音频")
            print("  [媒体]   注意: 音频通过会议桥路由")
            
            # 连接到会议桥
            try:
                pj.Lib.instance().conf_connect(call_slot, 0)
                pj.Lib.instance().conf_connect(0, call_slot)
                print("  [媒体] ✓ 会议桥已连接")
            except Exception as e:
                print(f"  [媒体] 警告: 会议桥连接失败: {e}")
            
            # 启动音频捕获线程
            if self.call_system:
                self.call_system.start_audio_capture(call_slot)
    
    def toggle_mute(self):
        """切换静音"""
        try:
            info = self.call.info()
            if info.state != pj.CallState.CONFIRMED:
                return False, "呼叫未接通"
            
            call_slot = info.conf_slot
            
            if self.is_muted:
                pj.Lib.instance().conf_connect(0, call_slot)
                self.is_muted = False
                print("  [静音] 已取消静音")
                return True, "已取消静音"
            else:
                pj.Lib.instance().conf_disconnect(0, call_slot)
                self.is_muted = True
                print("  [静音] 已静音")
                return True, "已静音"
                
        except Exception as e:
            print(f"  [静音] 操作失败: {e}")
            return False, str(e)
    
    def start_recording(self, record_file):
        """开始录音 - 录制对方和本地的所有音频"""
        try:
            if self.is_recording:
                return False, "已在录音中"
            
            # 获取呼叫信息
            info = self.call.info()
            
            # 创建WAV录音器
            self.wav_recorder = pj.Lib.instance().create_recorder(record_file)
            self.recorder_id = pj.Lib.instance().recorder_get_slot(self.wav_recorder)
            
            # 连接对方音频到录音器（对方说的话）
            pj.Lib.instance().conf_connect(info.conf_slot, self.recorder_id)
            
            # 也连接本地音频到录音器（你说的话，如果有的话）
            pj.Lib.instance().conf_connect(0, self.recorder_id)
            
            self.is_recording = True
            print(f"  [录音] ✓ 开始录制: {os.path.basename(record_file)}")
            print(f"  [录音] 录制内容: 对方语音 + 本地音频")
            print(f"  [录音] 提示: 通话结束后可以回放录音文件")
            return True, "录音已开始"
            
        except Exception as e:
            print(f"  [录音] 失败: {e}")
            return False, str(e)
    
    def stop_recording(self):
        """停止录音"""
        if not self.is_recording:
            return False, "未在录音"
            
        try:
            # 尝试断开连接，但忽略错误（因为呼叫可能已经结束）
            try:
                info = self.call.info()
                if info.conf_slot >= 0 and self.recorder_id >= 0:
                    pj.Lib.instance().conf_disconnect(info.conf_slot, self.recorder_id)
                    pj.Lib.instance().conf_disconnect(0, self.recorder_id)
            except:
                pass  # 呼叫已结束，连接已自动断开
            
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


class WebSocketCallSystem:
    """WebSocket双向通话系统核心"""
    
    def __init__(self):
        self.lib = None
        self.acc = None
        self.transport = None
        self.current_call = None
        self.current_callback = None
        
        # 命令队列
        self.command_queue = queue.Queue()
        self.result_queue = queue.Queue()
        
        # WebSocket客户端管理
        self.ws_clients = set()
        self.ws_server = None
        
        # 音频播放器和录音器（用于音频流捕获）
        self.audio_player = None
        self.audio_recorder = None
        self.player_slot = None
        self.recorder_slot = None
        
        # 创建录音目录
        os.makedirs(CONFIG['recordings_dir'], exist_ok=True)
    
    def start_audio_capture(self, call_slot):
        """启动音频捕获和录音"""
        print("  [音频] 启动录音和实时音频流...")
        
        # 1. 启动WAV文件录音
        if self.current_callback:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            record_file = os.path.join(CONFIG['recordings_dir'], f"call_{timestamp}.wav")
            
            success, msg = self.current_callback.start_recording(record_file)
            if success:
                print(f"  [音频] ✓ 自动录音已启动: {os.path.basename(record_file)}")
            else:
                print(f"  [音频] ✗ 录音启动失败: {msg}")
        
        # 2. 启动WebSocket音频流
        # 注意：PJSUA库对管道支持有bug，暂时禁用实时流
        # self.start_audio_stream_capture(call_slot)
        print("  [音频流] ⚠️ WebSocket实时音频流因PJSUA库限制暂时禁用")
        print("  [音频流] 💡 方案: 录音功能正常，通话后立即播放录音即可")
    
    def start_audio_stream_capture(self, call_slot):
        """启动音频流捕获（改进版 - 先启动读取线程）"""
        import os
        
        pipe_path = '/tmp/sip_to_browser.pcm'
        
        # 清理旧管道
        try:
            if os.path.exists(pipe_path):
                os.remove(pipe_path)
        except:
            pass
        
        # 创建命名管道
        try:
            os.mkfifo(pipe_path)
            print(f"  [音频流] ✓ 创建音频管道: {pipe_path}")
        except Exception as e:
            print(f"  [音频流] ✗ 创建管道失败: {e}")
            return False
        
        # 关键：先启动读取线程，再创建录音器
        # 这样管道就有读取端了，不会阻塞
        
        def pipe_reader():
            """管道读取线程 - 必须先启动"""
            print("  [音频流] 读取线程已启动，等待数据...")
            try:
                # 打开管道（会阻塞直到有写入端）
                with open(pipe_path, 'rb') as f:
                    print("  [音频流] ✓ 管道已打开，开始接收音频")
                    packet_count = 0
                    
                    while self.current_call and not self.current_callback.call_ended:
                        # 每次读取20ms的音频 (8kHz, 16-bit, 单声道 = 320 bytes)
                        data = f.read(320)
                        
                        if data and len(data) == 320:
                            # 放入队列，发送到WebSocket
                            if not audio_from_sip_queue.full():
                                audio_from_sip_queue.put(data, block=False)
                                packet_count += 1
                                
                                # 每50个包打印一次（1秒）
                                if packet_count % 50 == 0:
                                    print(f"  [音频流] 已发送 {packet_count} 个音频包 ({packet_count/50:.0f}秒)")
                        elif not data:
                            # 管道被关闭
                            break
                        else:
                            # 数据不完整，继续读
                            time.sleep(0.001)
                            
            except Exception as e:
                print(f"  [音频流] 读取错误: {e}")
            finally:
                print("  [音频流] 读取线程已停止")
                # 清理管道
                try:
                    os.remove(pipe_path)
                except:
                    pass
        
        # 先启动读取线程
        reader_thread = threading.Thread(target=pipe_reader, daemon=True)
        reader_thread.start()
        
        # 等待一下让读取线程准备好
        time.sleep(0.2)
        
        # 现在创建录音器（写入端）
        try:
            print("  [音频流] 创建录音器...")
            self.audio_stream_recorder = pj.Lib.instance().create_recorder(pipe_path)
            stream_recorder_slot = pj.Lib.instance().recorder_get_slot(self.audio_stream_recorder)
            
            # 连接呼叫音频到流录音器
            pj.Lib.instance().conf_connect(call_slot, stream_recorder_slot)
            
            print("  [音频流] ✓ 音频流已启动")
            print("  [音频流] 路径: SIP → PJSIP → 管道 → WebSocket → 浏览器")
            
            return True
            
        except Exception as e:
            import traceback
            print(f"  [音频流] ✗ 启动失败: {e}")
            traceback.print_exc()
            return False
    
    def start_audio_pipe_capture(self, call_slot):
        """使用文件管道捕获音频流到WebSocket"""
        import os
        
        pipe_path = '/tmp/sip_to_browser.pcm'
        
        # 清理旧管道
        try:
            if os.path.exists(pipe_path):
                os.remove(pipe_path)
        except:
            pass
        
        # 创建命名管道
        try:
            os.mkfifo(pipe_path)
            print(f"  [音频流] ✓ 创建音频管道: {pipe_path}")
        except Exception as e:
            print(f"  [音频流] ✗ 创建管道失败: {e}")
            return False
        
        try:
            # 创建录音器写入管道
            try:
                self.audio_pipe_recorder = pj.Lib.instance().create_recorder(pipe_path)
                pipe_recorder_slot = pj.Lib.instance().recorder_get_slot(self.audio_pipe_recorder)
            except Exception as rec_err:
                print(f"  [音频流] ✗ 创建录音器失败: {rec_err}")
                # 可能是因为管道还没有读取端，延迟处理
                import time
                time.sleep(0.5)
                self.audio_pipe_recorder = pj.Lib.instance().create_recorder(pipe_path)
                pipe_recorder_slot = pj.Lib.instance().recorder_get_slot(self.audio_pipe_recorder)
            
            # 连接呼叫音频到管道录音器（不影响原有录音）
            pj.Lib.instance().conf_connect(call_slot, pipe_recorder_slot)
            
            print("  [音频流] ✓ 会议桥已连接到音频管道")
            
            # 启动管道读取线程
            def pipe_reader():
                print("  [音频流] 读取线程已启动")
                try:
                    # 非阻塞打开（在线程中所以没问题）
                    with open(pipe_path, 'rb') as f:
                        packet_count = 0
                        while self.current_call and not self.current_callback.call_ended:
                            # 每次读取20ms的音频 (8kHz, 16bit, 单声道 = 160 samples * 2 bytes = 320 bytes)
                            data = f.read(320)
                            
                            if data and len(data) == 320:
                                # 放入队列，发送到WebSocket
                                if not audio_from_sip_queue.full():
                                    audio_from_sip_queue.put(data, block=False)
                                    packet_count += 1
                                    
                                    # 每50个包打印一次（1秒）
                                    if packet_count % 50 == 0:
                                        print(f"  [音频流] 已发送 {packet_count} 个音频包到WebSocket")
                            else:
                                # 管道可能被关闭或没有数据
                                time.sleep(0.01)
                                
                except Exception as e:
                    print(f"  [音频流] 读取错误: {e}")
                finally:
                    print("  [音频流] 读取线程已停止")
                    # 清理管道
                    try:
                        os.remove(pipe_path)
                    except:
                        pass
            
            # 启动线程
            reader_thread = threading.Thread(target=pipe_reader, daemon=True)
            reader_thread.start()
            
            print("  [音频流] ✓ 音频流已启动")
            print("  [音频流] 路径: SIP → 管道 → WebSocket → 浏览器扬声器")
            
            return True
            
        except Exception as e:
            import traceback
            print(f"  [音频流] ✗ 启动失败: {e}")
            print(f"  [音频流] 详细错误:")
            traceback.print_exc()
            try:
                os.remove(pipe_path)
            except:
                pass
            return False
        
    def broadcast_to_clients(self, message):
        """广播消息给所有WebSocket客户端"""
        if not self.ws_clients:
            return
            
        message_json = json.dumps(message)
        disconnected = set()
        
        for client in self.ws_clients:
            try:
                asyncio.run(client.send(message_json))
            except:
                disconnected.add(client)
        
        # 清理断开的客户端
        self.ws_clients -= disconnected
    
    async def handle_websocket_client(self, websocket):
        """处理WebSocket客户端连接"""
        print(f"\n[WebSocket] 新客户端连接")
        self.ws_clients.add(websocket)
        
        try:
            # 发送欢迎消息
            await websocket.send(json.dumps({
                'type': 'welcome',
                'message': 'WebSocket音频流已连接',
                'sample_rate': CONFIG['sample_rate'],
                'channels': CONFIG['channels']
            }))
            
            async for message in websocket:
                try:
                    if isinstance(message, bytes):
                        # 接收到音频数据（浏览器麦克风 -> SIP）
                        if not audio_to_sip_queue.full():
                            audio_to_sip_queue.put(message, block=False)
                    else:
                        # 接收到控制消息
                        data = json.loads(message)
                        await self.handle_ws_control_message(websocket, data)
                        
                except Exception as e:
                    print(f"[WebSocket] 处理消息错误: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            print(f"[WebSocket] 客户端断开: {websocket.remote_address}")
        finally:
            self.ws_clients.discard(websocket)
    
    async def handle_ws_control_message(self, websocket, data):
        """处理WebSocket控制消息"""
        msg_type = data.get('type')
        
        if msg_type == 'ping':
            await websocket.send(json.dumps({'type': 'pong'}))
            
        elif msg_type == 'request_status':
            status = self.get_call_status()
            await websocket.send(json.dumps({
                'type': 'status',
                'status': status
            }))
    
    async def audio_sender_loop(self):
        """持续发送音频流到WebSocket客户端"""
        print("[WebSocket] 音频发送循环已启动")
        
        while True:
            try:
                # 从队列获取SIP音频数据
                if not audio_from_sip_queue.empty():
                    audio_data = audio_from_sip_queue.get(timeout=0.1)
                    
                    # 发送给所有连接的客户端
                    disconnected = set()
                    for client in self.ws_clients:
                        try:
                            await client.send(audio_data)
                        except:
                            disconnected.add(client)
                    
                    # 清理断开的客户端
                    self.ws_clients -= disconnected
                else:
                    await asyncio.sleep(0.01)
                    
            except Exception as e:
                print(f"[WebSocket] 音频发送错误: {e}")
                await asyncio.sleep(0.1)
    
    def start_websocket_server(self):
        """启动WebSocket服务器"""
        async def run_server():
            print(f"\n[WebSocket] 启动服务器: ws://{CONFIG['ws_host']}:{CONFIG['ws_port']}")
            
            async with websockets.serve(
                self.handle_websocket_client,
                CONFIG['ws_host'],
                CONFIG['ws_port'],
                max_size=10*1024*1024,  # 10MB
                ping_interval=None
            ):
                # 同时运行音频发送循环
                await self.audio_sender_loop()
        
        # 在新线程中运行asyncio事件循环
        def run_in_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(run_server())
        
        ws_thread = threading.Thread(target=run_in_thread, daemon=True)
        ws_thread.start()
        
        print("[WebSocket] ✓ WebSocket服务器线程已启动")
    
    def start(self):
        """启动通话系统"""
        print("=" * 70)
        print("SIP WebSocket 双向实时通话系统")
        print("=" * 70)
        print(f"\n配置:")
        print(f"  SIP服务器: {CONFIG['server']}:{CONFIG['port']}")
        print(f"  主叫号码: {CONFIG['caller_number']}")
        print(f"  被叫前缀: {CONFIG['prefix']}")
        print(f"  WebSocket: ws://localhost:{CONFIG['ws_port']}")
        print(f"  HTTP API: http://localhost:{CONFIG['api_port']}")
        print(f"  音频格式: {CONFIG['sample_rate']}Hz, {CONFIG['channels']}ch, 16-bit PCM")
        print("=" * 70 + "\n")
        
        try:
            # 创建库实例
            self.lib = pj.Lib()
            
            # 配置媒体
            media_cfg = pj.MediaConfig()
            media_cfg.enable_ice = False
            media_cfg.no_vad = True
            media_cfg.ec_tail_len = 200
            media_cfg.clock_rate = CONFIG['sample_rate']
            media_cfg.snd_auto_close_time = -1
            
            # 初始化
            self.lib.init(
                log_cfg=pj.LogConfig(level=LOG_LEVEL, callback=None),
                media_cfg=media_cfg
            )
            
            # 创建UDP传输
            self.transport = self.lib.create_transport(pj.TransportType.UDP, pj.TransportConfig(0))
            print(f"✓ SIP传输: {self.transport.info().host}:{self.transport.info().port}")
            
            # 启动库
            self.lib.start()
            
            # 使用null音频设备（通过WebSocket传输音频）
            try:
                self.lib.set_null_snd_dev()
                print("✓ 音频设备: null设备（WebSocket模式）\n")
            except:
                pass
            
            # 创建账户
            acc_cfg = pj.AccountConfig()
            acc_cfg.id = f"sip:{CONFIG['caller_number']}@{CONFIG['server']}"
            acc_cfg.reg_uri = ""
            
            self.acc = self.lib.create_account(acc_cfg)
            print("✓ SIP账户已创建")
            
            # 启动WebSocket服务器
            self.start_websocket_server()
            time.sleep(1)  # 等待WebSocket启动
            
            print("\n" + "=" * 70)
            print("✓ 系统已启动！")
            print("=" * 70)
            print("\n📱 打开浏览器访问: http://localhost:8089")
            print("🎤 允许麦克风权限后即可开始通话\n")
            
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
            return {'success': False, 'error': '超时'}
    
    def _make_call_internal(self, phone_number):
        """内部呼叫方法"""
        if not self.acc:
            return None
        
        if self.current_call:
            try:
                info = self.current_call.info()
                if info.state != pj.CallState.DISCONNECTED:
                    print("✗ 已有活动呼叫")
                    return None
            except:
                pass
        
        full_number = f"{CONFIG['prefix']}{phone_number}"
        sip_uri = f"sip:{full_number}@{CONFIG['server']}:{CONFIG['port']}"
        
        print(f"\n发起呼叫:")
        print(f"  目标号码: {phone_number}")
        print(f"  完整号码: {full_number}")
        
        try:
            self.current_callback = WebSocketCallCallback(call_system=self)
            self.current_call = self.acc.make_call(sip_uri, cb=self.current_callback)
            
            print("✓ 呼叫已发起")
            return self.current_call
            
        except pj.Error as e:
            print(f"✗ 呼叫失败: {e}")
            return None
    
    def hangup(self):
        """挂断呼叫"""
        self.command_queue.put(('hangup', None))
        try:
            result = self.result_queue.get(timeout=2)
            return result
        except queue.Empty:
            return False
    
    def _hangup_internal(self):
        """内部挂断"""
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
    
    def get_call_status(self):
        """获取呼叫状态"""
        if not self.current_callback:
            return None
        
        try:
            return {
                'connected': self.current_callback.call_connected,
                'ended': self.current_callback.call_ended,
                'duration': time.time() - self.current_callback.start_time,
                'is_muted': self.current_callback.is_muted,
                'is_recording': self.current_callback.is_recording,
                'ws_clients': len(self.ws_clients)
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
        
        print("\n系统已停止")


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
        """发送HTML控制页面（包含WebSocket音频客户端）"""
        html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>WebSocket双向通话</title>
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
            max-width: 700px;
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
        .status-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            margin-bottom: 20px;
        }
        .status-disconnected { background: #f5f5f5; color: #666; }
        .status-connecting { background: #fff3cd; color: #856404; }
        .status-connected { background: #d4edda; color: #155724; }
        
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
        .btn-call:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .btn-hangup {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            flex: 1;
        }
        .btn-hangup:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(245, 87, 108, 0.4); }
        
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
            height: 300px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.5;
        }
        .log-time { color: #858585; }
        .log-success { color: #43e97b; }
        .log-error { color: #f5576c; }
        .log-info { color: #4facfe; }
        .log-warn { color: #ffa500; }
        
        .audio-indicator {
            margin-top: 15px;
            padding: 15px;
            background: #e8f5e9;
            border-radius: 10px;
            border-left: 4px solid #43e97b;
        }
        .audio-indicator.error {
            background: #ffebee;
            border-left-color: #f5576c;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎙️ WebSocket双向实时通话</h1>
        <p class="subtitle">印度尼西亚线路 | 浏览器音频模式</p>
        
        <div class="status-badge" id="wsStatus">未连接</div>
        
        <div class="call-section">
            <div class="input-group">
                <input type="text" id="phone" placeholder="输入号码 (例如: 82121065486)">
                <button class="btn-call" id="callBtn" onclick="makeCall()">📞 拨号</button>
            </div>
            <div class="input-group">
                <button class="btn-hangup" onclick="hangup()">📵 挂断</button>
            </div>
        </div>
        
        <div class="audio-indicator" id="audioStatus" style="display:none;">
            <div id="audioMessage">正在初始化音频...</div>
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
                <span class="status-label">WebSocket</span>
                <span class="status-value" id="ws-state">未连接</span>
            </div>
            <div class="status-item">
                <span class="status-label">音频流</span>
                <span class="status-value" id="audio-state">未启动</span>
            </div>
        </div>
        
        <div style="margin-top: 20px;">
            <div id="log">系统初始化中...</div>
        </div>
    </div>
    
    <script>
        let ws = null;
        let audioContext = null;
        let mediaStream = null;
        let audioProcessor = null;
        let isCallActive = false;
        let statusInterval = null;
        let audioChunksReceived = 0;
        
        function log(msg, type = 'info') {
            const logEl = document.getElementById('log');
            const time = new Date().toLocaleTimeString();
            let className = 'log-info';
            if (type === 'success') className = 'log-success';
            if (type === 'error') className = 'log-error';
            if (type === 'warn') className = 'log-warn';
            
            logEl.innerHTML += `<span class="log-time">[${time}]</span> <span class="${className}">${msg}</span><br>`;
            logEl.scrollTop = logEl.scrollHeight;
        }
        
        function updateWSStatus(status) {
            const badge = document.getElementById('wsStatus');
            const wsState = document.getElementById('ws-state');
            
            if (status === 'connected') {
                badge.textContent = 'WebSocket已连接';
                badge.className = 'status-badge status-connected';
                wsState.textContent = '已连接';
                wsState.className = 'status-value connected';
            } else if (status === 'connecting') {
                badge.textContent = 'WebSocket连接中...';
                badge.className = 'status-badge status-connecting';
                wsState.textContent = '连接中';
                wsState.className = 'status-value';
            } else {
                badge.textContent = 'WebSocket未连接';
                badge.className = 'status-badge status-disconnected';
                wsState.textContent = '未连接';
                wsState.className = 'status-value disconnected';
            }
        }
        
        async function initAudio() {
            try {
                log('🎤 请求麦克风权限...', 'info');
                
                // 请求麦克风访问
                mediaStream = await navigator.mediaDevices.getUserMedia({ 
                    audio: {
                        echoCancellation: true,
                        noiseSuppression: true,
                        autoGainControl: true,
                        sampleRate: 8000
                    } 
                });
                
                log('✓ 麦克风权限已获取', 'success');
                
                // 创建音频上下文
                audioContext = new (window.AudioContext || window.webkitAudioContext)({
                    sampleRate: 8000
                });
                
                log(`✓ 音频上下文已创建 (${audioContext.sampleRate}Hz)`, 'success');
                
                // 创建音频源
                const source = audioContext.createMediaStreamSource(mediaStream);
                
                // 创建处理器
                audioProcessor = audioContext.createScriptProcessor(2048, 1, 1);
                
                audioProcessor.onaudioprocess = (e) => {
                    if (ws && ws.readyState === WebSocket.OPEN && isCallActive) {
                        const inputData = e.inputBuffer.getChannelData(0);
                        
                        // 转换为16位PCM
                        const pcmData = new Int16Array(inputData.length);
                        for (let i = 0; i < inputData.length; i++) {
                            pcmData[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768));
                        }
                        
                        // 发送到WebSocket
                        ws.send(pcmData.buffer);
                    }
                };
                
                source.connect(audioProcessor);
                audioProcessor.connect(audioContext.destination);
                
                document.getElementById('audioStatus').style.display = 'block';
                document.getElementById('audioStatus').className = 'audio-indicator';
                document.getElementById('audioMessage').textContent = '✓ 麦克风已就绪，可以开始通话';
                document.getElementById('audio-state').textContent = '已就绪';
                document.getElementById('audio-state').className = 'status-value connected';
                
                log('✓ 音频处理器已启动', 'success');
                
            } catch (err) {
                log(`⚠ 无法访问麦克风: ${err.message}`, 'warn');
                log('💡 继续以【只听模式】运行（可以听到对方，对方听不到你）', 'info');
                
                // 创建只接收的音频上下文（不需要麦克风）
                try {
                    audioContext = new (window.AudioContext || window.webkitAudioContext)({
                        sampleRate: 8000
                    });
                    log('✓ 音频输出已初始化', 'success');
                } catch (e) {
                    log(`✗ 音频输出初始化失败: ${e.message}`, 'error');
                }
                
                document.getElementById('audioStatus').style.display = 'block';
                document.getElementById('audioStatus').className = 'audio-indicator';
                document.getElementById('audioMessage').textContent = '⚠ 只听模式（无麦克风权限，可以听到对方）';
                document.getElementById('audio-state').textContent = '只听模式';
                document.getElementById('audio-state').className = 'status-value connecting';
            }
        }
        
        function playAudioData(audioData) {
            if (!audioContext) return;
            
            try {
                // 将接收到的PCM数据转换为Float32Array
                const int16Array = new Int16Array(audioData);
                const float32Array = new Float32Array(int16Array.length);
                
                for (let i = 0; i < int16Array.length; i++) {
                    float32Array[i] = int16Array[i] / 32768.0;
                }
                
                // 创建音频缓冲区并播放
                const audioBuffer = audioContext.createBuffer(1, float32Array.length, audioContext.sampleRate);
                audioBuffer.getChannelData(0).set(float32Array);
                
                const source = audioContext.createBufferSource();
                source.buffer = audioBuffer;
                source.connect(audioContext.destination);
                source.start();
                
                audioChunksReceived++;
                if (audioChunksReceived % 50 === 0) {
                    log(`🔊 已接收 ${audioChunksReceived} 个音频包`, 'info');
                }
                
            } catch (err) {
                console.error('播放音频失败:', err);
            }
        }
        
        function connectWebSocket() {
            updateWSStatus('connecting');
            log('📡 连接WebSocket服务器...', 'info');
            
            ws = new WebSocket('ws://' + window.location.hostname + ':8090');
            ws.binaryType = 'arraybuffer';
            
            ws.onopen = () => {
                updateWSStatus('connected');
                log('✓ WebSocket已连接', 'success');
            };
            
            ws.onmessage = (event) => {
                if (event.data instanceof ArrayBuffer) {
                    // 接收到音频数据
                    playAudioData(event.data);
                } else {
                    // 接收到控制消息
                    try {
                        const data = JSON.parse(event.data);
                        handleWSMessage(data);
                    } catch (e) {
                        console.error('解析消息失败:', e);
                    }
                }
            };
            
            ws.onerror = (error) => {
                log('✗ WebSocket错误', 'error');
                updateWSStatus('disconnected');
            };
            
            ws.onclose = () => {
                log('⚠ WebSocket连接关闭', 'warn');
                updateWSStatus('disconnected');
                
                // 5秒后重连
                setTimeout(() => {
                    log('🔄 尝试重新连接...', 'info');
                    connectWebSocket();
                }, 5000);
            };
        }
        
        function handleWSMessage(data) {
            if (data.type === 'welcome') {
                log(`✓ ${data.message}`, 'success');
                log(`ℹ️ 音频格式: ${data.sample_rate}Hz, ${data.channels}ch`, 'info');
            } else if (data.type === 'call_state') {
                log(`📞 ${data.message} (${data.elapsed.toFixed(1)}s)`, 'info');
                
                if (data.connected) {
                    isCallActive = true;
                    document.getElementById('call-state').textContent = '已接通';
                    document.getElementById('call-state').className = 'status-value connected';
                    audioChunksReceived = 0;
                }
                
                if (data.message === '呼叫结束') {
                    isCallActive = false;
                    document.getElementById('call-state').textContent = '已结束';
                    document.getElementById('call-state').className = 'status-value disconnected';
                }
            }
        }
        
        function makeCall() {
            const phone = document.getElementById('phone').value.trim();
            if (!phone) {
                alert('请输入号码');
                return;
            }
            
            if (!audioContext) {
                alert('音频未就绪，请刷新页面重试');
                return;
            }
            
            log(`📞 正在拨打: ${phone}`, 'info');
            
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
            log('📵 正在挂断...', 'info');
            
            fetch('/api/hangup', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    log(`✓ ${data.message}`, 'success');
                    isCallActive = false;
                } else {
                    log(`✗ ${data.error}`, 'error');
                }
            })
            .catch(e => log(`✗ 请求失败: ${e}`, 'error'));
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
                    document.getElementById('call-duration').textContent = Math.floor(s.duration) + '秒';
                    
                    if (s.connected) {
                        document.getElementById('call-state').textContent = '通话中';
                        document.getElementById('call-state').className = 'status-value connected';
                    }
                } else {
                    if (statusInterval) {
                        clearInterval(statusInterval);
                        statusInterval = null;
                    }
                }
            })
            .catch(() => {});
        }
        
        // 页面加载时初始化
        window.onload = () => {
            log('✓ 系统已加载', 'success');
            log('ℹ️ 初始化音频系统...', 'info');
            
            // 初始化音频
            initAudio();
            
            // 连接WebSocket
            setTimeout(() => {
                connectWebSocket();
            }, 500);
            
            log('📱 准备就绪，可以开始拨号', 'success');
        };
        
        // 页面卸载时清理
        window.onbeforeunload = () => {
            if (ws) ws.close();
            if (mediaStream) {
                mediaStream.getTracks().forEach(track => track.stop());
            }
            if (audioContext) {
                audioContext.close();
            }
        };
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
    
    # 尝试启用HTTPS
    protocol = "http"
    try:
        cert_file = os.path.join(os.path.dirname(__file__), 'cert.pem')
        key_file = os.path.join(os.path.dirname(__file__), 'key.pem')
        if os.path.exists(cert_file) and os.path.exists(key_file):
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(cert_file, key_file)
            server.socket = context.wrap_socket(server.socket, server_side=True)
            protocol = "https"
            print(f"✓ HTTPS已启用")
    except Exception as e:
        print(f"⚠ HTTPS启用失败，使用HTTP: {e}")
    
    print(f"✓ API服务器: {protocol}://0.0.0.0:{CONFIG['api_port']}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


def main():
    """主函数"""
    print("\n启动WebSocket双向通话系统...\n")
    
    # 创建通话系统
    call_system = WebSocketCallSystem()
    
    if not call_system.start():
        print("系统启动失败")
        sys.exit(1)
    
    # 在新线程中启动API服务器
    api_thread = threading.Thread(target=run_api_server, args=(call_system,), daemon=True)
    api_thread.start()
    
    time.sleep(1)
    
    print("按 Ctrl+C 停止系统\n")
    print("💡 提示: 命令队列处理已启动\n")
    
    try:
        # 主循环：处理命令队列（必须在主线程，PJSUA要求）
        while True:
            try:
                # 非阻塞获取命令
                cmd, data = call_system.command_queue.get(timeout=0.1)
                
                print(f"[主循环] 收到命令: {cmd}")
                
                if cmd == 'call':
                    result = call_system._make_call_internal(data)
                    call_system.result_queue.put({'success': result is not None, 'call': result})
                    
                elif cmd == 'hangup':
                    result = call_system._hangup_internal()
                    call_system.result_queue.put(result)
                    
            except queue.Empty:
                # 没有命令，继续循环
                pass
            
            # 短暂休眠，不要占用太多CPU
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        print("\n\n正在停止系统...")
        call_system.stop()


if __name__ == "__main__":
    main()

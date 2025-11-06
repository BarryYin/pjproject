#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单IVR系统 - 印度尼西亚线路
功能:
1. 自动拨号
2. 播放录音给客户
3. 录制通话内容
4. HTTP API控制
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

# 配置
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
    'api_port': 8088
}

LOG_LEVEL = CONFIG['log_level']


class IVRCallCallback(pj.CallCallback):
    """IVR呼叫回调"""
    
    def __init__(self, call=None, ivr_system=None):
        pj.CallCallback.__init__(self, call)
        self.ivr_system = ivr_system
        self.call_connected = False
        self.call_ended = False
        self.start_time = time.time()
        self.connect_time = None
        self.player_id = None
        self.recorder_id = None
        self.wav_player = None
        self.wav_recorder = None
        
    def on_state(self):
        """呼叫状态变化"""
        info = self.call.info()
        elapsed = time.time() - self.start_time
        
        print(f"\n[{elapsed:.1f}s] 呼叫状态: {info.state_text}")
        print(f"  远程: {info.remote_uri}")
        print(f"  响应: {info.last_code} ({info.last_reason})")
        
        if info.state == pj.CallState.CONFIRMED:
            self.call_connected = True
            self.connect_time = time.time()
            print("  >>> 呼叫已接通!")
            
            # 接通后通知IVR系统（不要在新线程中执行）
            if self.ivr_system:
                self.ivr_system.command_queue.put(('ivr_start', self))
            
        elif info.state == pj.CallState.DISCONNECTED:
            self.call_ended = True
            duration = time.time() - self.start_time
            print(f"  >>> 呼叫结束 (总时长: {duration:.1f}秒)")
            
            # 清理资源
            self.cleanup()
            
    def on_media_state(self):
        """媒体状态变化"""
        info = self.call.info()
        if info.media_state == pj.MediaState.ACTIVE:
            call_slot = info.conf_slot
            
            # 连接音频会议桥
            pj.Lib.instance().conf_connect(call_slot, 0)
            pj.Lib.instance().conf_connect(0, call_slot)
            print("  [媒体] 音频通道已激活")
            
    def play_file(self, audio_file):
        """播放音频文件给对方"""
        try:
            info = self.call.info()
            if info.state != pj.CallState.CONFIRMED:
                print("  [播放] 呼叫未接通，无法播放")
                return False
            
            if not os.path.exists(audio_file):
                print(f"  [播放] 文件不存在: {audio_file}")
                return False
            
            # 停止之前的播放
            if self.wav_player:
                try:
                    pj.Lib.instance().conf_disconnect(self.player_id, info.conf_slot)
                    self.wav_player = None
                except:
                    pass
            
            # 创建播放器
            self.wav_player = pj.Lib.instance().create_player(audio_file, loop=False)
            self.player_id = pj.Lib.instance().player_get_slot(self.wav_player)
            
            # 连接播放器到呼叫
            pj.Lib.instance().conf_connect(self.player_id, info.conf_slot)
            
            print(f"  [播放] 正在播放: {os.path.basename(audio_file)}")
            return True
            
        except Exception as e:
            print(f"  [播放] 失败: {e}")
            return False
    
    def start_recording(self, record_file):
        """开始录音"""
        try:
            info = self.call.info()
            if info.state != pj.CallState.CONFIRMED:
                print("  [录音] 呼叫未接通，无法录音")
                return False
            
            # 停止之前的录音
            if self.wav_recorder:
                try:
                    pj.Lib.instance().conf_disconnect(info.conf_slot, self.recorder_id)
                    self.wav_recorder = None
                except:
                    pass
            
            # 创建录音器
            self.wav_recorder = pj.Lib.instance().create_recorder(record_file)
            self.recorder_id = pj.Lib.instance().recorder_get_slot(self.wav_recorder)
            
            # 连接呼叫到录音器
            pj.Lib.instance().conf_connect(info.conf_slot, self.recorder_id)
            pj.Lib.instance().conf_connect(0, self.recorder_id)  # 也录制本地麦克风
            
            print(f"  [录音] 开始录制: {os.path.basename(record_file)}")
            return True
            
        except Exception as e:
            print(f"  [录音] 失败: {e}")
            return False
    
    def stop_recording(self):
        """停止录音"""
        if self.wav_recorder:
            try:
                info = self.call.info()
                pj.Lib.instance().conf_disconnect(info.conf_slot, self.recorder_id)
                pj.Lib.instance().conf_disconnect(0, self.recorder_id)
                self.wav_recorder = None
                print("  [录音] 已停止")
            except Exception as e:
                print(f"  [录音] 停止失败: {e}")
    
    def cleanup(self):
        """清理资源"""
        if self.wav_player:
            try:
                self.wav_player = None
            except:
                pass
                
        if self.wav_recorder:
            try:
                self.stop_recording()
            except:
                pass


class IVRSystem:
    """IVR系统核心"""
    
    def __init__(self):
        self.lib = None
        self.acc = None
        self.transport = None
        self.current_call = None
        self.current_callback = None
        
        # 命令队列 - 用于线程安全的通信
        self.command_queue = queue.Queue()
        self.result_queue = queue.Queue()
        
        # 创建必要的目录
        os.makedirs(CONFIG['audio_dir'], exist_ok=True)
        os.makedirs(CONFIG['recordings_dir'], exist_ok=True)
        
    def start(self):
        """启动IVR系统"""
        print("=" * 70)
        print("IVR系统 - 印度尼西亚线路")
        print("=" * 70)
        print(f"\n配置:")
        print(f"  SIP服务器: {CONFIG['server']}:{CONFIG['port']}")
        print(f"  主叫号码: {CONFIG['caller_number']}")
        print(f"  被叫前缀: {CONFIG['prefix']}")
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
            
            # 设置null音频设备（服务器模式）
            try:
                self.lib.set_null_snd_dev()
                print("✓ 音频设备: null设备（服务器模式）")
            except:
                pass
            
            # 创建账户
            acc_cfg = pj.AccountConfig()
            acc_cfg.id = f"sip:{CONFIG['caller_number']}@{CONFIG['server']}"
            acc_cfg.reg_uri = ""
            
            self.acc = self.lib.create_account(acc_cfg)
            print("✓ 账户已创建\n")
            
            print("=" * 70)
            print("IVR系统已启动!")
            print("=" * 70)
            
            return True
            
        except pj.Error as e:
            print(f"\n✗ 启动失败: {e}")
            return False
    
    def make_call(self, phone_number):
        """发起呼叫（线程安全）"""
        # 将命令放入队列，由主线程处理
        self.command_queue.put(('call', phone_number))
        
        # 等待结果（最多5秒）
        try:
            result = self.result_queue.get(timeout=5)
            return result
        except queue.Empty:
            print("✗ 呼叫请求超时")
            return None
    
    def _make_call_internal(self, phone_number):
        """内部呼叫方法（在PJSUA线程中调用）"""
        if not self.acc:
            print("✗ 账户未初始化")
            return None
        
        # 构造完整号码
        full_number = f"{CONFIG['prefix']}{phone_number}"
        sip_uri = f"sip:{full_number}@{CONFIG['server']}:{CONFIG['port']}"
        
        print(f"\n发起呼叫:")
        print(f"  目标号码: {phone_number}")
        print(f"  完整号码: {full_number}")
        print(f"  SIP URI: {sip_uri}")
        
        try:
            # 创建呼叫回调
            self.current_callback = IVRCallCallback(ivr_system=self)
            self.current_call = self.acc.make_call(sip_uri, cb=self.current_callback)
            
            print("✓ 呼叫已发起")
            return self.current_call
            
        except pj.Error as e:
            print(f"✗ 呼叫失败: {e}")
            return None
    
    def on_call_connected(self, call_callback):
        """呼叫接通后的IVR流程"""
        print("\n[IVR] 开始执行IVR流程...")
        
        # 等待1秒，让媒体稳定
        time.sleep(1)
        
        # 1. 开始录音
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        record_file = os.path.join(CONFIG['recordings_dir'], f"call_{timestamp}.wav")
        call_callback.start_recording(record_file)
        
        # 2. 播放欢迎语音（如果存在）
        welcome_file = os.path.join(CONFIG['audio_dir'], "welcome.wav")
        if os.path.exists(welcome_file):
            call_callback.play_file(welcome_file)
            time.sleep(3)  # 等待播放完成（根据实际音频长度调整）
        
        # 3. 可以继续播放其他内容或等待用户输入
        # 这里可以添加更复杂的IVR逻辑
        
        print("[IVR] IVR流程执行完成")
    
    def hangup_current_call(self):
        """挂断当前呼叫（线程安全）"""
        # 将命令放入队列，由主线程处理
        self.command_queue.put(('hangup', None))
        
        # 等待结果
        try:
            result = self.result_queue.get(timeout=2)
            return result
        except queue.Empty:
            return False
    
    def _hangup_internal(self):
        """内部挂断方法（在PJSUA线程中调用）"""
        if self.current_call:
            try:
                self.current_call.hangup()
                print("✓ 呼叫已挂断")
                return True
            except:
                return False
        return False
    
    def stop(self):
        """停止IVR系统"""
        if self.current_call:
            self.hangup_current_call()
            
        if self.lib:
            try:
                self.lib.destroy()
            except:
                pass
        
        print("\nIVR系统已停止")


class APIHandler(BaseHTTPRequestHandler):
    """HTTP API处理器"""
    
    ivr_system = None  # 将由主程序设置
    
    def do_POST(self):
        """处理POST请求"""
        path = urlparse(self.path).path
        
        # 读取请求体
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
        elif path == '/api/status':
            self.handle_status(data)
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
        
        call = self.ivr_system.make_call(phone_number)
        
        if call:
            self.send_json_response({
                'success': True,
                'message': '呼叫已发起',
                'phone_number': phone_number
            })
        else:
            self.send_error_response("呼叫失败")
    
    def handle_hangup(self, data):
        """处理挂断请求"""
        result = self.ivr_system.hangup_current_call()
        
        if result:
            self.send_json_response({
                'success': True,
                'message': '呼叫已挂断'
            })
        else:
            self.send_error_response("没有活动的呼叫")
    
    def handle_status(self, data):
        """获取系统状态"""
        has_call = self.ivr_system.current_call is not None
        
        self.send_json_response({
            'success': True,
            'has_active_call': has_call
        })
    
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
    <title>IVR控制面板</title>
    <style>
        body { font-family: Arial; max-width: 600px; margin: 50px auto; padding: 20px; }
        h1 { color: #333; }
        input, button { padding: 10px; margin: 5px; font-size: 16px; }
        button { background: #4CAF50; color: white; border: none; cursor: pointer; }
        button:hover { background: #45a049; }
        .hangup { background: #f44336; }
        .hangup:hover { background: #da190b; }
        #log { background: #f5f5f5; padding: 15px; margin-top: 20px; 
               height: 300px; overflow-y: auto; font-family: monospace; }
    </style>
</head>
<body>
    <h1>📞 IVR控制面板</h1>
    <p>印度尼西亚线路</p>
    
    <div>
        <input type="text" id="phone" placeholder="输入号码 (例如: 82121065486)" style="width: 300px;">
        <button onclick="makeCall()">拨号</button>
        <button class="hangup" onclick="hangup()">挂断</button>
    </div>
    
    <div id="log">系统就绪...</div>
    
    <script>
        function log(msg) {
            const logEl = document.getElementById('log');
            const time = new Date().toLocaleTimeString();
            logEl.innerHTML += `[${time}] ${msg}<br>`;
            logEl.scrollTop = logEl.scrollHeight;
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
                    log(`✓ ${data.message}`);
                } else {
                    log(`✗ ${data.error}`);
                }
            })
            .catch(e => log(`✗ 请求失败: ${e}`));
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
                    log(`✓ ${data.message}`);
                } else {
                    log(`✗ ${data.error}`);
                }
            })
            .catch(e => log(`✗ 请求失败: ${e}`));
        }
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


def run_api_server(ivr_system):
    """运行API服务器"""
    APIHandler.ivr_system = ivr_system
    
    server = HTTPServer((CONFIG['api_host'], CONFIG['api_port']), APIHandler)
    print(f"✓ API服务器启动: http://8.222.33.80:{CONFIG['api_port']}")
    print(f"  控制面板: http://8.222.33.80:{CONFIG['api_port']}/")
    print()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


def main():
    """主函数"""
    print("\n启动IVR系统...\n")
    
    # 创建IVR系统
    ivr = IVRSystem()
    
    if not ivr.start():
        print("系统启动失败")
        sys.exit(1)
    
    # 在新线程中启动API服务器
    api_thread = threading.Thread(target=run_api_server, args=(ivr,), daemon=True)
    api_thread.start()
    
    print("\n按 Ctrl+C 停止系统\n")
    
    try:
        while True:
            # 处理命令队列（在主线程/PJSUA线程中）
            try:
                cmd, data = ivr.command_queue.get(timeout=0.1)
                
                if cmd == 'call':
                    result = ivr._make_call_internal(data)
                    ivr.result_queue.put(result)
                    
                elif cmd == 'hangup':
                    result = ivr._hangup_internal()
                    ivr.result_queue.put(result)
                    
                elif cmd == 'ivr_start':
                    # 执行IVR流程（data是call_callback对象）
                    ivr.on_call_connected(data)
                    
            except queue.Empty:
                pass
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n\n正在停止系统...")
        ivr.stop()


if __name__ == "__main__":
    main()

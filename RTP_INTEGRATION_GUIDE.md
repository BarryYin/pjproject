# RTP音频流集成指南

## 🎯 核心原理

根据你找到的资料，SIP通话的音频传输过程：

```
1. SIP信令层 (PJSIP处理) ✅
   ├─ INVITE (建立通话)
   ├─ SDP协商 (交换IP、端口、编解码器)
   └─ 200 OK, ACK (确认连接)

2. RTP媒体层 (需要捕获) 🔄
   ├─ 对方: 麦克风 → 编码 → RTP包 → 发送到我们的IP:Port
   ├─ 我们: 监听Port → 接收RTP包 → 解码 → 扬声器
   └─ 我们需要在这里插入WebSocket转发
```

## 📊 当前实现状态

### ✅ 已实现
- SIP信令完全正常（PJSIP处理）
- SDP协商成功（可以看到呼叫接通）
- 会议桥连接
- 录音功能（证明RTP已被接收）

### 🔄 需要实现
- 捕获RTP音频数据
- 转发到WebSocket
- 浏览器播放

## 🔧 三种实现方案

### 方案1: RTP端口镜像 ⭐ 推荐

**原理**: 监听PJSIP使用的RTP端口，复制音频数据

**优点**:
- 纯Python实现
- 不修改PJSIP
- 相对简单

**实现步骤**:

1. **获取PJSIP的RTP端口**

```python
# 在呼叫接通后
def on_media_state(self):
    info = self.call.info()
    if info.media_state == pj.MediaState.ACTIVE:
        # 获取媒体传输信息
        call_info = info
        
        # PJSIP会分配一个RTP端口
        # 通常在SDP中可以看到
        # 需要从PJSIP API获取实际端口号
```

2. **启动RTP桥接器**

```python
from rtp_audio_bridge import RTPAudioBridge

# 创建桥接器
rtp_bridge = RTPAudioBridge()

# 设置音频数据回调
def on_audio_data(audio_payload):
    # 发送到WebSocket
    for client in ws_clients:
        await client.send(audio_payload)

rtp_bridge.set_audio_callback(on_audio_data)

# 启动监听（使用PJSIP的RTP端口）
rtp_bridge.start(rtp_port)
```

**挑战**: 
- 需要准确获取PJSIP使用的RTP端口
- 可能需要处理SRTP加密

### 方案2: 会议桥音频捕获

**原理**: 使用PJSIP的会议桥接口捕获音频

**关键代码**:

```python
# 创建一个"空"播放器用于捕获
class AudioCapturePort:
    def __init__(self):
        self.captured_audio = []
    
    def on_frame(self, frame):
        # 这里会收到音频帧
        self.captured_audio.append(frame)
        # 发送到WebSocket
        send_to_websocket(frame)

# 连接到会议桥
lib.conf_connect(call_slot, capture_port_slot)
```

**挑战**:
- PJSUA Python绑定可能没有暴露这个API

### 方案3: 使用文件管道 ⭐ 最简单

**原理**: PJSIP写入文件，Python读取文件

**实现**:

```python
import os

# 1. 创建命名管道
os.mkfifo('/tmp/sip_audio_out.pcm')

# 2. PJSIP录音器写入管道
recorder = lib.create_recorder('/tmp/sip_audio_out.pcm')
lib.conf_connect(call_slot, recorder_slot)

# 3. Python线程读取管道并发送到WebSocket
def pipe_to_websocket():
    with open('/tmp/sip_audio_out.pcm', 'rb') as f:
        while True:
            # 读取20ms的音频 (8000Hz, 16bit, 单声道)
            data = f.read(320)  # 160 samples * 2 bytes
            if data:
                # 发送到WebSocket
                for client in ws_clients:
                    await client.send(data)

# 启动线程
threading.Thread(target=pipe_to_websocket, daemon=True).start()
```

**优点**:
- 最简单实现
- 不需要RTP知识
- 使用PJSIP已有功能

**缺点**:
- 有一定延迟
- 需要管道管理

## 🚀 推荐实现路径

### 第一步: 文件管道快速验证

```python
# 修改 sip_websocket_call_system.py

def start_audio_capture(self, call_slot):
    """使用文件管道捕获音频"""
    
    # 创建管道
    pipe_path = '/tmp/sip_to_websocket.pcm'
    try:
        os.mkfifo(pipe_path)
    except FileExistsError:
        pass
    
    # 创建录音器到管道
    recorder = pj.Lib.instance().create_recorder(pipe_path)
    recorder_slot = pj.Lib.instance().recorder_get_slot(recorder)
    
    # 连接呼叫音频到录音器
    pj.Lib.instance().conf_connect(call_slot, recorder_slot)
    
    # 启动管道读取线程
    def pipe_reader():
        with open(pipe_path, 'rb') as f:
            while self.current_call:
                data = f.read(320)  # 20ms @ 8kHz
                if data:
                    # 放入队列
                    audio_from_sip_queue.put(data)
    
    threading.Thread(target=pipe_reader, daemon=True).start()
```

### 第二步: 集成到WebSocket

```python
# WebSocket音频发送已经实现
async def audio_sender_loop(self):
    while True:
        if not audio_from_sip_queue.empty():
            audio_data = audio_from_sip_queue.get()
            
            # 发送给所有客户端
            for client in self.ws_clients:
                await client.send(audio_data)
```

### 第三步: 浏览器播放

```javascript
// 已实现
ws.onmessage = (event) => {
    if (event.data instanceof ArrayBuffer) {
        playAudioData(event.data);
    }
};
```

## 📝 完整实现示例

```python
# 在 WebSocketCallSystem 类中添加

def start_audio_pipe_capture(self, call_slot):
    """启动文件管道音频捕获"""
    import os
    import threading
    
    pipe_path = '/tmp/sip_to_browser.pcm'
    
    # 创建管道
    try:
        if os.path.exists(pipe_path):
            os.remove(pipe_path)
        os.mkfifo(pipe_path)
        print(f"[音频管道] ✓ 创建管道: {pipe_path}")
    except Exception as e:
        print(f"[音频管道] ✗ 创建失败: {e}")
        return False
    
    try:
        # 创建录音器
        self.audio_pipe_recorder = pj.Lib.instance().create_recorder(pipe_path)
        recorder_slot = pj.Lib.instance().recorder_get_slot(self.audio_pipe_recorder)
        
        # 连接呼叫音频到录音器
        pj.Lib.instance().conf_connect(call_slot, recorder_slot)
        
        print("[音频管道] ✓ 会议桥已连接到管道")
        
        # 启动管道读取线程
        def pipe_reader():
            print("[音频管道] 读取线程已启动")
            try:
                with open(pipe_path, 'rb') as f:
                    while self.current_call and not self.current_callback.call_ended:
                        # 读取20ms的音频 (8kHz, 16bit, 单声道 = 320字节)
                        data = f.read(320)
                        if data and len(data) == 320:
                            # 放入队列，发送到WebSocket
                            if not audio_from_sip_queue.full():
                                audio_from_sip_queue.put(data)
                        else:
                            time.sleep(0.01)  # 避免忙等待
            except Exception as e:
                print(f"[音频管道] 读取错误: {e}")
            finally:
                print("[音频管道] 读取线程已停止")
        
        reader_thread = threading.Thread(target=pipe_reader, daemon=True)
        reader_thread.start()
        
        print("[音频管道] ✓ 音频流已启动")
        print("[音频管道] SIP音频 → 管道 → WebSocket → 浏览器")
        
        return True
        
    except Exception as e:
        print(f"[音频管道] ✗ 启动失败: {e}")
        return False
```

## 🧪 测试步骤

1. **修改代码**: 在 `start_audio_capture` 中调用 `start_audio_pipe_capture`
2. **启动系统**: `python3 sip_websocket_call_system.py`
3. **拨打电话**: 浏览器中拨号
4. **观察日志**: 看是否有"音频流已启动"
5. **检查浏览器**: 控制台是否收到音频数据
6. **验证播放**: 是否能听到声音

## ⚠️ 注意事项

### 文件管道方式

1. **管道清理**: 程序退出前删除管道文件
2. **阻塞问题**: open() 可能阻塞，需要在线程中执行
3. **缓冲控制**: 及时读取避免缓冲溢出

### RTP方式

1. **端口获取**: 需要准确获取PJSIP的RTP端口
2. **RTP解析**: 需要正确解析RTP头
3. **编解码**: 可能需要处理不同的codec

## 📊 性能指标

### 文件管道方式
- **延迟**: 50-200ms
- **CPU**: 低
- **实现难度**: ⭐

### RTP方式  
- **延迟**: 20-100ms
- **CPU**: 中
- **实现难度**: ⭐⭐⭐

## 🎯 总结

**最佳实践**:
1. 先用**文件管道**快速实现
2. 验证端到端流程正常
3. 如需优化再考虑RTP方式

**关键代码位置**:
- 修改: `sip_websocket_call_system.py` 的 `start_audio_capture()` 方法
- 使用: 文件管道 + 线程读取
- 目标: 将音频数据放入 `audio_from_sip_queue`

**预期效果**:
- 浏览器实时听到对方声音
- WebSocket持续接收音频数据
- 延迟在可接受范围内

---

**下一步**: 实现文件管道版本，快速验证完整流程！

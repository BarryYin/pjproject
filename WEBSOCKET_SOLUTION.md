# WebSocket音频流解决方案

## 问题分析

经过深入研究PJSIP源码，发现以下事实：

### PJSIP架构

```
RTP层 → pjmedia_port → Conference Bridge → 音频设备
                ↓
         get_frame()  ← 这是关键！
         put_frame()
```

### Python绑定限制

PJSUA Python绑定**没有**暴露以下关键API：
- `pjmedia_port_get_frame()` - 获取音频帧
- `pjmedia_port_put_frame()` - 写入音频帧  
- 自定义媒体端口创建

### 为什么录音器能工作

```python
recorder = pj.Lib.instance().create_recorder("file.wav")
# 内部实现：
# 1. 创建pjmedia_wav_writer_port
# 2. 连接到会议桥
# 3. 会议桥自动调用 put_frame() 写入音频
```

录音器是C层实现的完整媒体端口，有自己的 `put_frame()` 回调。

### 为什么管道方案失败

```python
recorder = create_recorder("/tmp/pipe.pcm")  # ✗ 失败
```

原因：
1. PJSUA内部对文件路径有严格检查
2. Python绑定的异常处理有bug ("exceptions must derive from BaseException")
3. 管道操作在C层会阻塞或崩溃

## 可行方案

### 方案1: 编写C扩展 ⭐ (最正确)

创建自定义media port：

```c
// custom_websocket_port.c
typedef struct {
    pjmedia_port base;
    websocket_connection *ws;
    pj_pool_t *pool;
} websocket_port;

static pj_status_t get_frame(pjmedia_port *port, pjmedia_frame *frame) {
    websocket_port *wport = (websocket_port*)port;
    // 从WebSocket读取音频
    websocket_read(wport->ws, frame->buf, frame->size);
    return PJ_SUCCESS;
}

static pj_status_t put_frame(pjmedia_port *port, const pjmedia_frame *frame) {
    websocket_port *wport = (websocket_port*)port;
    // 发送音频到WebSocket
    websocket_send(wport->ws, frame->buf, frame->size);
    return PJ_SUCCESS;
}

PJ_DEF(pj_status_t) create_websocket_port(pj_pool_t *pool, 
                                           websocket_connection *ws,
                                           pjmedia_port **p_port) {
    websocket_port *port;
    port = PJ_POOL_ZALLOC_T(pool, websocket_port);
    
    pjmedia_port_info_init(&port->base.info, "websocket", ...);
    port->base.get_frame = &get_frame;
    port->base.put_frame = &put_frame;
    port->ws = ws;
    
    *p_port = &port->base;
    return PJ_SUCCESS;
}
```

然后在Python中：
```python
import custom_websocket_port
port = custom_websocket_port.create(websocket_connection)
port_slot = pj.Lib.instance().conf_add_port(port)
pj.Lib.instance().conf_connect(call_slot, port_slot)  # 对方 → WS
pj.Lib.instance().conf_connect(port_slot, call_slot)  # WS → 对方
```

### 方案2: 使用PJSUA2 (现代API)

PJSUA2是C++接口，比PJSUA更强大：

```cpp
class WebSocketAudioMedia : public AudioMedia {
public:
    virtual void onFrameReceived(MediaFrame &frame) {
        // 发送到WebSocket
        websocket.send(frame.buf, frame.size);
    }
};
```

### 方案3: RTP端口镜像

直接监听RTP端口，捕获UDP包：

```python
# 获取RTP端口
transport_info = call.info().media[0].transport
rtp_port = transport_info.local_rtcp_port - 1  # RTP = RTCP - 1

# 监听UDP
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', rtp_port))

while True:
    data, addr = sock.recvfrom(2048)
    # 解析RTP包
    rtp_header = data[:12]
    rtp_payload = data[12:]  # 这就是音频数据！
    
    # 发送到WebSocket
    await websocket.send(rtp_payload)
```

### 方案4: 使用JsSIP (纯Web)

不依赖Python后端，直接在浏览器实现SIP：

```
浏览器 (JsSIP + WebRTC) ←WebSocket→ WebSocket-SIP网关 ←UDP→ SIP服务器
```

需要：
1. WebSocket到UDP的协议转换网关
2. 可能需要TURN/STUN服务器处理NAT

## 当前状态

✅ **录音方案完全可用** - 延迟3-5秒
❌ **实时WebSocket流** - PJSUA Python绑定限制
🔄 **JsSIP方案** - 需要网关和防火墙配置

## 推荐

对于生产环境：
1. **短期**：使用录音方案，通话后立即播放
2. **中期**：编写C扩展实现WebSocket端口
3. **长期**：迁移到PJSUA2或使用专业WebRTC网关

对于学习：
1. 研究PJSIP示例代码 (pjsip-apps/src/samples/)
2. 阅读 pjmedia/port.h 文档
3. 尝试编译修改 simple_pjsua.c

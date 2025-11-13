# 阿里云NLS WebSocket支持说明

## ✓ 确认：阿里云NLS SDK完全支持WebSocket

### WebSocket连接地址

阿里云NLS服务**默认使用WebSocket协议**，连接地址为：

```
wss://nls-gateway.cn-shanghai.aliyuncs.com/ws/v1
```

### 支持的服务

所有NLS服务都通过WebSocket实现：

1. **TTS (语音合成)** - `NlsSpeechSynthesizer`
   - 默认URL: `wss://nls-gateway.cn-shanghai.aliyuncs.com/ws/v1`
   
2. **ASR (一句话识别)** - `NlsSpeechRecognizer`
   - 默认URL: `wss://nls-gateway.cn-shanghai.aliyuncs.com/ws/v1`
   
3. **实时语音识别** - `NlsSpeechTranscriber`
   - 默认URL: `wss://nls-gateway.cn-shanghai.aliyuncs.com/ws/v1`
   
4. **流式语音合成** - `NlsStreamInputTts`
   - 默认URL: `wss://nls-gateway.cn-shanghai.aliyuncs.com/ws/v1`

### SDK内部实现

SDK内置了完整的WebSocket客户端实现：

```
alibabacloud-nls-python-sdk/
├── nls/
│   ├── websocket/           # WebSocket客户端库
│   │   ├── _core.py        # WebSocket核心实现
│   │   ├── _app.py         # WebSocketApp (类似JavaScript WebSocket对象)
│   │   ├── _handshake.py   # WebSocket握手协议
│   │   ├── _abnf.py        # WebSocket帧协议
│   │   └── ...
│   ├── core.py             # NLS核心，使用websocket.WebSocketApp
│   ├── speech_synthesizer.py   # TTS实现
│   ├── speech_recognizer.py    # ASR实现
│   └── speech_transcriber.py   # 实时识别实现
```

### WebSocket协议特性

SDK支持完整的WebSocket特性：

- ✅ **WSS (WebSocket Secure)** - 使用TLS加密
- ✅ **二进制数据传输** - 支持音频流传输
- ✅ **文本消息** - JSON格式的控制消息
- ✅ **Ping/Pong心跳** - 保持连接活跃
- ✅ **异步回调** - 实时接收服务端消息
- ✅ **连接管理** - 自动处理连接、重连、关闭

### 代码示例

#### 1. TTS通过WebSocket

```python
import nls
from nls.token import getToken

token = getToken(AKID, AKKEY)

# 创建TTS实例（自动使用WebSocket）
tts = nls.NlsSpeechSynthesizer(
    token=token,
    appkey=APPKEY,
    on_data=on_data_callback,
    on_completed=on_completed_callback
)

# 启动合成（通过WebSocket连接）
tts.start(
    text="要合成的文本",
    voice="indah",
    aformat="wav",
    sample_rate=16000
)
```

#### 2. ASR通过WebSocket

```python
import nls
from nls.token import getToken

token = getToken(AKID, AKKEY)

# 创建ASR实例（自动使用WebSocket）
sr = nls.NlsSpeechRecognizer(
    token=token,
    appkey=APPKEY,
    on_result_changed=on_result_changed_callback,
    on_completed=on_completed_callback
)

# 启动识别（通过WebSocket连接）
sr.start(aformat="pcm", sample_rate=16000)

# 发送音频数据（通过WebSocket）
sr.send_audio(audio_data)

# 结束识别
sr.stop()
```

#### 3. 自定义WebSocket URL

如果需要使用自定义WebSocket地址（如内网地址）：

```python
# 外网WebSocket地址（默认）
url = "wss://nls-gateway.cn-shanghai.aliyuncs.com/ws/v1"

# 内网WebSocket地址（阿里云ECS内网访问）
url_internal = "ws://nls-gateway-cn-shanghai-internal.aliyuncs.com/ws/v1"

# 使用自定义URL
tts = nls.NlsSpeechSynthesizer(
    url=url_internal,  # 指定WebSocket URL
    token=token,
    appkey=APPKEY
)
```

### WebSocket连接流程

```
客户端                                  阿里云NLS服务器
  |                                           |
  |---- WebSocket握手请求 ------------------>|
  |     (wss://nls-gateway...../ws/v1)       |
  |                                           |
  |<--- WebSocket握手响应 --------------------|
  |     (101 Switching Protocols)            |
  |                                           |
  |==== WebSocket连接建立 ====================|
  |                                           |
  |---- 发送开始请求 (JSON) ------------------>|
  |     {"header": {...}, "payload": {...}}  |
  |                                           |
  |<--- 返回开始确认 (JSON) -------------------|
  |                                           |
  |---- 发送音频数据 (Binary) ---------------->| (ASR)
  |     或接收音频数据 (Binary) <-------------|  (TTS)
  |                                           |
  |<--- 返回识别结果 (JSON) -------------------|
  |                                           |
  |---- 发送结束请求 (JSON) ------------------>|
  |                                           |
  |<--- 返回完成消息 (JSON) -------------------|
  |                                           |
  |---- WebSocket关闭 ------------------------>|
  |                                           |
```

### WebSocket消息格式

#### 控制消息（JSON文本）

```json
{
  "header": {
    "message_id": "uuid",
    "task_id": "uuid",
    "namespace": "SpeechSynthesizer",
    "name": "StartSynthesis",
    "appkey": "your_appkey"
  },
  "payload": {
    "text": "要合成的文本",
    "voice": "indah",
    "format": "wav",
    "sample_rate": 16000
  }
}
```

#### 音频数据（二进制）

通过WebSocket的OPCODE_BINARY发送/接收原始音频数据。

### 优势

相比HTTP REST API，WebSocket提供：

1. **低延迟** - 无需重复建立连接
2. **实时双向通信** - 服务器可主动推送消息
3. **流式传输** - 支持音频流实时传输和识别
4. **高效** - 减少HTTP头部开销
5. **连接保持** - 长连接避免频繁握手

### 内网访问

如果您的应用部署在阿里云上海ECS（华东2），可使用内网WebSocket地址：

```python
# 内网WebSocket地址（无公网流量费用）
url = "ws://nls-gateway-cn-shanghai-internal.aliyuncs.com/ws/v1"
```

**注意**：
- 需要使用专有网络（VPC）
- 经典网络不支持内网访问

### 调试

启用WebSocket调试日志：

```python
import nls

# 启用调试日志
nls.enableTrace(True)

# 创建服务实例...
```

这将输出详细的WebSocket通信日志，包括：
- 连接建立
- 消息发送/接收
- 错误信息
- 连接关闭

## 总结

✅ **阿里云NLS SDK完全基于WebSocket实现**
✅ **所有服务（TTS、ASR、实时识别）都使用WebSocket**
✅ **SDK内置完整WebSocket客户端，无需额外配置**
✅ **支持WSS加密传输**
✅ **支持实时双向通信和流式传输**

您可以直接使用现有的测试脚本，它们已经在使用WebSocket协议！

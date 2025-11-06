# 双向实时通话系统 - 快速开始

## 🎯 系统说明

这是一个真正的**双向实时语音通话系统**，不是播放录音！

- ✅ 你说话 → 对方能听见（通过麦克风）
- ✅ 对方说话 → 你能听见（通过扬声器）
- ✅ 支持静音、录音、挂断等操作
- ✅ Web界面控制 + HTTP API

## 🚀 快速启动

### 方法1: 使用启动脚本（推荐）

```bash
cd /home/henry/pjproject
./start_live_call.sh
```

### 方法2: 直接运行

```bash
cd /home/henry/pjproject
python3 sip_live_call_system.py
```

启动成功后，你会看到：

```
======================================================================
✓ 双向实时通话系统已启动!
======================================================================

按 Ctrl+C 停止系统

提示:
  - 接通后可以直接对话，双向实时通话
  - 使用Web界面控制：静音、录音等
  - 录音会保存双方的声音

✓ API服务器启动: http://localhost:8089
  控制面板: http://localhost:8089/
```

## 🌐 使用Web界面

1. 打开浏览器，访问：`http://localhost:8089`
2. 在输入框中输入号码（例如：`82121065486`）
3. 点击 **📞 拨号** 按钮
4. 等待接通
5. **接通后就可以直接对话了！**

### 通话中的操作

- **静音**：点击 "🔇 静音/取消静音" 按钮（对方听不到你的声音）
- **录音**：点击 "⏺️ 开始录音" 开始录制，再次点击停止
- **挂断**：点击 "📵 挂断" 按钮

## 📡 使用HTTP API

### 1. 拨号

```bash
curl -X POST http://localhost:8089/api/call \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "82121065486"}'
```

响应：
```json
{
  "success": true,
  "message": "呼叫已发起",
  "phone_number": "82121065486"
}
```

### 2. 查看状态

```bash
curl -X POST http://localhost:8089/api/status
```

响应：
```json
{
  "success": true,
  "status": {
    "connected": false,
    "ended": false,
    "duration": 6.09,
    "is_muted": false,
    "is_recording": false
  }
}
```

### 3. 静音/取消静音

```bash
curl -X POST http://localhost:8089/api/mute
```

### 4. 开始录音

```bash
curl -X POST http://localhost:8089/api/record/start
```

录音文件会保存到：`/home/henry/pjproject/recordings/call_YYYYMMDD_HHMMSS.wav`

### 5. 停止录音

```bash
curl -X POST http://localhost:8089/api/record/stop
```

### 6. 挂断

```bash
curl -X POST http://localhost:8089/api/hangup
```

## 📊 测试示例

完整的测试流程：

```bash
# 1. 查看初始状态
curl -X POST http://localhost:8089/api/status

# 2. 发起呼叫
curl -X POST http://localhost:8089/api/call \
  -H "Content-Type: application/json" \
  -d '{"phone_number":"82121065486"}'

# 3. 等待几秒后查看状态
sleep 5
curl -X POST http://localhost:8089/api/status

# 4. 开始录音
curl -X POST http://localhost:8089/api/record/start

# 5. 通话一段时间...

# 6. 停止录音
curl -X POST http://localhost:8089/api/record/stop

# 7. 挂断
curl -X POST http://localhost:8089/api/hangup
```

## 📝 实际测试日志

```
发起呼叫:
  目标号码: 82121065486
  完整号码: 1346282121065486
  SIP URI: sip:1346282121065486@147.139.205.88:5060

[0.0s] 呼叫状态: CALLING
  远程: sip:1346282121065486@147.139.205.88:5060
  >>> 正在发起呼叫...

[2.4s] 呼叫状态: EARLY
  >>> 会话进行中...
  [媒体] ✓ 双向音频通道已激活
  [媒体]   对方声音 -> 你的扬声器
  [媒体]   你的麦克风 -> 对方

[8.2s] 呼叫状态: DISCONNECTED
  >>> 呼叫结束 (总时长: 8.2秒)
```

## ⚠️ 重要提示

### 音频设备

当前服务器环境只有虚拟音频设备（null），不会有真实声音：

```
[PulseAudio 输出设备] 共 1 个:
  ✓ auto_null  ⚠ 虚拟设备
```

**要实现真正的双向通话，需要：**

1. **本地运行**：在有真实麦克风和扬声器的本地机器上运行
2. **音频转发**：配置PulseAudio网络音频转发（较复杂）
3. **远程桌面**：使用支持音频转发的远程桌面连接

### SIP配置

- 服务器：`147.139.205.88:5060`
- 主叫号码：`6281479242434`
- 被叫前缀：`13462`（自动添加）
- 拨打格式：输入 `82121065486` → 实际拨打 `1346282121065486`

## 🆚 与IVR系统的区别

| 功能 | IVR系统 | 双向通话系统 |
|------|---------|--------------|
| 播放录音 | ✅ | ❌ |
| 双向实时通话 | ❌ | ✅ |
| 麦克风输入 | ❌ | ✅ |
| 扬声器输出 | ❌ | ✅ |
| 使用场景 | 自动语音播报 | 真人对话 |

## 📂 相关文件

- `sip_live_call_system.py` - 主程序
- `start_live_call.sh` - 启动脚本
- `LIVE_CALL_GUIDE.md` - 详细文档
- `recordings/` - 录音保存目录

## 🔧 停止系统

按 `Ctrl+C` 即可停止系统

## ❓ 常见问题

**Q: 点击拨号后没反应？**

A: 检查浏览器控制台（F12）和系统终端日志，确认API是否响应

**Q: 呼叫一直在振铃？**

A: 正常现象，等待对方接听。如果对方拒绝或无人接听会自动挂断

**Q: 听不到声音？**

A: 当前在服务器环境运行，只有虚拟音频设备。需要在本地有音频设备的机器上运行

**Q: 如何查看完整文档？**

A: 查看 `LIVE_CALL_GUIDE.md` 文件

---

**提示**：这是一个真正的实时通话系统，不是播放录音！接通后可以像打电话一样正常对话。

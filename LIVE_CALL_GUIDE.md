# SIP双向实时通话系统使用指南

## 系统简介

这是一个基于PJSIP的**双向实时语音通话系统**，支持：

✅ **真正的双向通话** - 你说话对方能听见，对方说话你也能听见  
✅ **自动音频设备检测** - 自动配置麦克风和扬声器  
✅ **Web控制界面** - 简单易用的网页操作面板  
✅ **通话录音** - 可录制双方的完整对话  
✅ **静音控制** - 随时静音/取消静音  
✅ **HTTP API** - 可编程控制所有功能  

## 快速开始

### 1. 启动系统

```bash
cd /home/henry/pjproject
python3 sip_live_call_system.py
```

### 2. 打开Web控制面板

在浏览器中访问：
```
http://localhost:8089
```

或者从外部访问（如果是服务器）：
```
http://你的服务器IP:8089
```

### 3. 拨打电话

1. 在输入框中输入目标号码（例如：`82121065486`）
2. 点击 **📞 拨号** 按钮
3. 等待对方接听
4. 接通后就可以开始双向对话了！

### 4. 通话中的操作

- **挂断**: 点击 "📵 挂断" 按钮
- **静音**: 点击 "🔇 静音/取消静音" 按钮（对方听不到你的声音）
- **录音**: 点击 "⏺️ 开始录音" 开始录制，再次点击停止

## 系统配置

### SIP服务器配置（印度尼西亚线路）

```python
CONFIG = {
    'server': '147.139.205.88',
    'port': 5060,
    'caller_number': '6281479242434',  # 主叫号码
    'prefix': '13462',                  # 被叫前缀
    'use_real_audio': True,             # 使用真实音频设备
    'api_port': 8089                    # Web服务端口
}
```

### 号码格式

系统会自动在号码前添加前缀：
- 输入: `82121065486`
- 实际拨打: `1346282121065486`

## 音频设备

### 本地环境（有麦克风和扬声器）

系统会自动检测并使用：
- ✅ 系统默认麦克风（输入）
- ✅ 系统默认扬声器（输出）

### 远程服务器环境

如果在没有音频设备的服务器上运行：
- ⚠️ 需要配置音频转发（如PulseAudio网络音频）
- ⚠️ 或者设置 `use_real_audio = False` 使用null设备（无声音）

## HTTP API 文档

### 1. 发起呼叫

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

### 2. 挂断电话

```bash
curl -X POST http://localhost:8089/api/hangup
```

### 3. 静音/取消静音

```bash
curl -X POST http://localhost:8089/api/mute
```

响应：
```json
{
  "success": true,
  "message": "已静音"  // 或 "已取消静音"
}
```

### 4. 开始录音

```bash
curl -X POST http://localhost:8089/api/record/start
```

录音文件会自动保存到：`/home/henry/pjproject/recordings/call_YYYYMMDD_HHMMSS.wav`

### 5. 停止录音

```bash
curl -X POST http://localhost:8089/api/record/stop
```

### 6. 获取通话状态

```bash
curl -X POST http://localhost:8089/api/status
```

响应：
```json
{
  "success": true,
  "status": {
    "state": "CONFIRMED",
    "connected": true,
    "remote_uri": "sip:1346282121065486@147.139.205.88:5060",
    "duration": 45.2,
    "is_muted": false,
    "is_recording": true
  }
}
```

## 技术原理

### 双向音频连接

系统通过PJSIP的音频会议桥实现双向音频：

```python
# 1. 对方的声音 -> 你的扬声器（你能听到对方）
pj.Lib.instance().conf_connect(call_slot, 0)

# 2. 你的麦克风 -> 对方（对方能听到你）
pj.Lib.instance().conf_connect(0, call_slot)
```

### 静音实现

静音时断开麦克风到对方的连接：
```python
# 静音：对方听不到你
pj.Lib.instance().conf_disconnect(0, call_slot)

# 取消静音：对方能听到你
pj.Lib.instance().conf_connect(0, call_slot)
```

### 录音实现

录音会同时录制双方的声音：
```python
# 录制对方的声音
pj.Lib.instance().conf_connect(call_slot, recorder_id)

# 录制自己的声音
pj.Lib.instance().conf_connect(0, recorder_id)
```

## 与IVR系统的区别

| 特性 | IVR系统 (`sip_ivr_system.py`) | 双向通话系统 (`sip_live_call_system.py`) |
|------|-------------------------------|------------------------------------------|
| 播放录音 | ✅ 支持 | ❌ 不支持（专注实时通话） |
| 双向对话 | ❌ 单向播放 | ✅ 真正的双向实时通话 |
| 麦克风 | ❌ 不使用 | ✅ 使用你的麦克风 |
| 扬声器 | ❌ 不使用 | ✅ 使用你的扬声器 |
| 使用场景 | 自动语音播报 | 真人对话、客服、会议 |

## 常见问题

### Q: 为什么听不到声音？

**A:** 检查以下几点：
1. 确认 `use_real_audio = True`
2. 检查系统音频设备：
   ```bash
   pactl list sinks short     # 检查输出设备
   pactl list sources short   # 检查输入设备
   ```
3. 如果是远程服务器，需要配置音频转发或在本地运行

### Q: 对方听不到我的声音？

**A:** 检查：
1. 麦克风是否被静音
2. 系统麦克风权限
3. 查看日志中的 "你的麦克风 -> 对方" 是否显示已连接

### Q: 我听不到对方的声音？

**A:** 检查：
1. 扬声器音量
2. 查看日志中的 "对方声音 -> 你的扬声器" 是否显示已连接

### Q: 如何在服务器环境使用？

**A:** 两个方案：
1. **推荐**: 在本地有音频设备的机器上运行
2. 配置PulseAudio网络音频转发（较复杂）

### Q: 录音文件在哪里？

**A:** 默认保存在：`/home/henry/pjproject/recordings/`

格式: `call_YYYYMMDD_HHMMSS.wav`

## 示例使用流程

### 1. 命令行测试

```bash
# 启动系统
python3 sip_live_call_system.py

# 在另一个终端用API拨号
curl -X POST http://localhost:8089/api/call \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "82121065486"}'

# 等待接通后，就可以和对方通话了

# 需要静音时
curl -X POST http://localhost:8089/api/mute

# 开始录音
curl -X POST http://localhost:8089/api/record/start

# 挂断
curl -X POST http://localhost:8089/api/hangup
```

### 2. Web界面操作

1. 打开浏览器访问 `http://localhost:8089`
2. 输入号码点击拨号
3. 接通后直接对话
4. 需要时点击静音或录音按钮
5. 完成后点击挂断

## 文件说明

- `sip_live_call_system.py` - 主程序
- `recordings/` - 录音保存目录
- `LIVE_CALL_GUIDE.md` - 本使用指南

## 相关文件

- `sip_ivr_system.py` - IVR系统（播放录音）
- `sip_test_call_indonesia.py` - 简单拨号测试
- `IVR_GUIDE.md` - IVR系统使用指南

---

**提示**: 这是一个真正的实时通话系统，不是播放录音！接通后你可以像打电话一样正常对话。

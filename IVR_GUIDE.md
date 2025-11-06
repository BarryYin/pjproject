# IVR系统使用指南

## 📋 功能特性

✅ **自动拨号** - HTTP API控制
✅ **播放录音** - 给客户播放欢迎语等
✅ **通话录制** - 自动录制所有通话
✅ **Web控制面板** - 浏览器操作
✅ **简单易用** - 无需复杂配置

---

## 🚀 快速启动

### 1. 启动IVR系统

```bash
cd /home/henry/pjproject
./sip_ivr_system.py
```

### 2. 打开控制面板

在浏览器打开：
```
http://8.222.33.80:8088/
```

### 3. 拨号测试

- 输入号码（例如：82121065486）
- 点击"拨号"
- 系统会自动：
  - 拨打电话
  - 开始录音
  - 播放欢迎语（如果有）

---

## 📁 目录结构

```
/home/henry/pjproject/
├── sip_ivr_system.py       # IVR系统主程序
├── audio_files/             # 音频文件目录
│   └── welcome.wav         # 欢迎语音（需要自己准备）
└── recordings/              # 录音文件目录
    └── call_20240101_120000.wav  # 自动生成的录音
```

---

## 🎵 准备音频文件

### 要求

- **格式**: WAV
- **采样率**: 8000 Hz
- **声道**: 单声道 (Mono)
- **位深度**: 16-bit

### 转换命令

如果你有其他格式的音频，用ffmpeg转换：

```bash
# 安装ffmpeg（如果没有）
apt-get install ffmpeg

# 转换音频
ffmpeg -i input.mp3 -ar 8000 -ac 1 -sample_fmt s16 audio_files/welcome.wav
```

### 示例音频

创建一个简单的测试音频：

```bash
# 使用文字转语音（需要安装espeak）
apt-get install espeak
espeak -v zh "欢迎致电,请稍候" -w audio_files/welcome.wav

# 然后转换格式
ffmpeg -i audio_files/welcome.wav -ar 8000 -ac 1 -sample_fmt s16 audio_files/welcome_8k.wav
mv audio_files/welcome_8k.wav audio_files/welcome.wav
```

---

## 🌐 HTTP API接口

### 1. 拨打电话

**请求**:
```bash
curl -X POST http://8.222.33.80:8088/api/call \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "82121065486"}'
```

**响应**:
```json
{
  "success": true,
  "message": "呼叫已发起",
  "phone_number": "82121065486"
}
```

### 2. 挂断电话

**请求**:
```bash
curl -X POST http://8.222.33.80:8088/api/hangup \
  -H "Content-Type: application/json"
```

**响应**:
```json
{
  "success": true,
  "message": "呼叫已挂断"
}
```

### 3. 查询状态

**请求**:
```bash
curl -X POST http://8.222.33.80:8088/api/status \
  -H "Content-Type: application/json"
```

**响应**:
```json
{
  "success": true,
  "has_active_call": false
}
```

---

## 🐍 Python调用示例

```python
import requests

API_URL = "http://8.222.33.80:8088"

# 拨号
response = requests.post(f"{API_URL}/api/call", json={
    "phone_number": "82121065486"
})
print(response.json())

# 等待通话
import time
time.sleep(30)

# 挂断
response = requests.post(f"{API_URL}/api/hangup")
print(response.json())
```

---

## ⚙️ 配置修改

编辑 `sip_ivr_system.py` 顶部的 CONFIG：

```python
CONFIG = {
    'server': '147.139.205.88',      # SIP服务器
    'port': 5060,                     # SIP端口
    'caller_number': '6281479242434', # 主叫号码
    'prefix': '13462',                # 被叫前缀
    
    # 音频文件路径
    'audio_dir': '/home/henry/pjproject/audio_files',
    'recordings_dir': '/home/henry/pjproject/recordings',
    
    # HTTP API配置
    'api_host': '0.0.0.0',           # 监听所有IP
    'api_port': 8088                  # API端口
}
```

---

## 🎬 IVR流程定制

修改 `on_call_connected` 方法来定制IVR流程：

```python
def on_call_connected(self, call_callback):
    """呼叫接通后的IVR流程"""
    print("\n[IVR] 开始执行IVR流程...")
    
    time.sleep(1)  # 等待媒体稳定
    
    # 1. 开始录音
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    record_file = os.path.join(CONFIG['recordings_dir'], f"call_{timestamp}.wav")
    call_callback.start_recording(record_file)
    
    # 2. 播放欢迎语
    welcome_file = os.path.join(CONFIG['audio_dir'], "welcome.wav")
    if os.path.exists(welcome_file):
        call_callback.play_file(welcome_file)
        time.sleep(5)  # 等待播放完成
    
    # 3. 播放更多内容
    msg_file = os.path.join(CONFIG['audio_dir'], "message.wav")
    if os.path.exists(msg_file):
        call_callback.play_file(msg_file)
        time.sleep(10)
    
    # 4. 这里可以添加更复杂的逻辑
    #    - 等待按键输入（DTMF）
    #    - 根据输入播放不同内容
    #    - 语音识别
    #    等等...
    
    print("[IVR] IVR流程执行完成")
```

---

## 📊 查看录音文件

```bash
# 列出所有录音
ls -lh /home/henry/pjproject/recordings/

# 播放录音（在有音频的机器上）
aplay /home/henry/pjproject/recordings/call_20240101_120000.wav

# 下载到本地
scp henry@8.222.33.80:/home/henry/pjproject/recordings/*.wav ~/Downloads/
```

---

## 🔧 故障排除

### 问题1: 听不到播放的音频

**原因**: 音频格式不正确

**解决**:
```bash
# 确保音频是8000Hz, 16-bit, mono
ffmpeg -i input.wav -ar 8000 -ac 1 -sample_fmt s16 output.wav
```

### 问题2: 录音文件为空

**原因**: 呼叫未接通或时间太短

**解决**: 确保对方接听，且通话时间足够长

### 问题3: API无法访问

**原因**: 防火墙阻止

**解决**:
```bash
# 开放端口
sudo ufw allow 8088/tcp
```

---

## 💡 使用场景

### 1. 自动外呼通知

```python
# 批量拨打
numbers = ["82121065486", "81234567890", "87654321098"]

for number in numbers:
    requests.post("http://8.222.33.80:8088/api/call", 
                  json={"phone_number": number})
    time.sleep(60)  # 等待1分钟
    requests.post("http://8.222.33.80:8088/api/hangup")
```

### 2. 语音通知系统

准备不同的音频文件：
- `welcome.wav` - 欢迎语
- `promotion.wav` - 促销信息
- `reminder.wav` - 提醒通知

### 3. 调查问卷

- 播放问题
- 收集按键（DTMF）
- 记录答案

---

## 🚀 下一步扩展

可以添加的功能：

1. **DTMF检测** - 接收用户按键
2. **语音识别** - ASR集成
3. **文字转语音** - TTS实时生成
4. **数据库记录** - 保存呼叫记录
5. **Web界面增强** - 实时通话状态
6. **多路并发** - 同时处理多个呼叫

需要哪个功能，告诉我，我帮你加！

---

## 📞 快速测试

```bash
# 1. 启动系统
./sip_ivr_system.py

# 2. 打开浏览器
http://8.222.33.80:8088/

# 3. 输入号码拨号
82121065486

# 4. 查看录音
ls -lh recordings/
```

完成！🎉

# 双向语音通信系统 使用指南

## 概述

这是一个基于PJSIP的完整双向语音通信系统，支持三种通信模式，可以灵活满足不同场景需求。

### 核心特性

- ✅ **接收对方声音** - 实时听到对方说话
- ✅ **发送自己声音** - 三种方式（麦克风/预录音频/混合）
- ✅ **通话录音** - 自动录制完整通话内容
- ✅ **HTTP API控制** - Web界面或API接口控制
- ✅ **音频队列管理** - 动态添加和播放音频文件

---

## 三种通信模式

### 模式1: 麦克风模式 (MICROPHONE)

**最接近真实电话通话体验**

#### 工作原理
```
对方声音 ──→ 本地扬声器 (你听到对方)
本地麦克风 ──→ 对方 (对方听到你)
```

#### 适用场景
- 本地开发测试
- 有音频设备的环境
- 需要实时互动的场景
- 人工客服

#### 启动方式
```bash
python3 sip_two_way_voice.py --mode microphone
```

#### 特点
- ✅ 真实双向通话，像打电话
- ✅ 零延迟，实时响应
- ✅ 支持麦克风和扬声器
- ❌ 需要音频硬件设备
- ❌ 不适合服务器环境

---

### 模式2: 音频队列模式 (AUDIO_QUEUE) 【推荐】

**服务器环境的标准方案**

#### 工作原理
```
对方声音 ──→ 本地（可选择是否输出）
预录音频文件 ──→ 队列播放 ──→ 对方听到
```

#### 适用场景
- ⭐ **服务器生产环境**（无麦克风）
- ⭐ **IVR语音菜单系统**
- ⭐ **自动化客服**
- 通知播报系统
- 录音播放服务

#### 启动方式
```bash
python3 sip_two_way_voice.py --mode audio_queue
```

#### 使用流程

1. **准备音频文件**
   ```bash
   # 音频文件放在这个目录
   /home/henry/pjproject/audio_files/
   
   # 支持格式: WAV (推荐), 8000Hz采样率
   ```

2. **拨打电话**
   ```bash
   # 通过API或Web界面拨号
   # 自动播放 welcome.wav (如果存在)
   ```

3. **动态添加音频**
   ```bash
   # 方式1: API接口
   curl -X POST http://localhost:8088/api/add_audio \
     -H "Content-Type: application/json" \
     -d '{"filename": "menu.wav"}'
   
   # 方式2: Web控制面板
   # 访问 http://localhost:8088
   # 输入文件名 → 点击"添加到队列"
   ```

4. **立即播放**
   ```bash
   # 不使用队列，立即打断当前播放
   curl -X POST http://localhost:8088/api/play_now \
     -H "Content-Type: application/json" \
     -d '{"filename": "urgent.wav"}'
   ```

#### 音频队列工作机制
```python
# 队列示例
队列: [welcome.wav] → [menu.wav] → [goodbye.wav]
        ↓
    自动播放线程
        ↓
    按顺序播放给对方
```

#### 特点
- ✅ **无需麦克风**，服务器友好
- ✅ 音频质量可控（预录制）
- ✅ 支持动态添加音频
- ✅ 自动队列管理
- ✅ 可录制对方语音
- ⚠️ 不能实时回应（只能播放预录音频）

---

### 模式3: 混合模式 (HYBRID)

**队列播放 + 语音录制的组合方案**

#### 工作原理
```
对方声音 ──→ 录音文件保存
预录音频队列 ──→ 自动播放 ──→ 对方
```

#### 适用场景
- 需要收集用户语音反馈
- 语音留言系统
- 调查问卷（播放问题 + 录制回答）
- 后续需要语音识别分析

#### 启动方式
```bash
python3 sip_two_way_voice.py --mode hybrid
```

#### 特点
- ✅ 结合队列播放和录音
- ✅ 适合收集语音反馈
- ✅ 可后续进行语音识别
- ⚠️ 仍然不能实时互动

---

## HTTP API 接口文档

### 基础URL
```
http://localhost:8088
```

### 1. 发起呼叫
```bash
POST /api/call
Content-Type: application/json

{
  "phone_number": "82121065486"
}

# 响应
{
  "success": true,
  "message": "呼叫已发起",
  "phone_number": "82121065486",
  "mode": "audio_queue"
}
```

### 2. 挂断呼叫
```bash
POST /api/hangup

# 响应
{
  "success": true,
  "message": "呼叫已挂断"
}
```

### 3. 添加音频到队列
```bash
POST /api/add_audio
Content-Type: application/json

{
  "filename": "menu.wav"
}

# 响应
{
  "success": true,
  "message": "已添加到队列: menu.wav",
  "queue_size": 3
}
```

### 4. 立即播放音频
```bash
POST /api/play_now
Content-Type: application/json

{
  "filename": "urgent.wav"
}

# 响应
{
  "success": true,
  "message": "正在播放: urgent.wav"
}
```

### 5. 获取系统状态
```bash
POST /api/status

# 响应
{
  "success": true,
  "has_active_call": true,
  "call_connected": true,
  "mode": "audio_queue",
  "queue_size": 2
}
```

### 6. 切换通信模式
```bash
POST /api/switch_mode
Content-Type: application/json

{
  "mode": "microphone"  # microphone / audio_queue / hybrid
}

# 响应
{
  "success": true,
  "message": "已切换到模式: microphone",
  "mode": "microphone"
}

# 注意: 只能在无活动呼叫时切换
```

---

## Web 控制面板

### 访问地址
```
http://localhost:8088/
```

### 功能
- 📞 **呼叫控制** - 拨号、挂断
- 🎵 **音频控制** - 添加队列、立即播放
- 🔄 **模式切换** - 实时切换通信模式
- 📊 **状态监控** - 实时显示系统状态
- 📝 **操作日志** - 所有操作实时日志

---

## 音频文件准备

### 推荐规格
```
格式: WAV
采样率: 8000 Hz
声道: 单声道 (Mono)
位深度: 16-bit
```

### 转换现有音频
```bash
# 使用 ffmpeg 转换
ffmpeg -i input.mp3 -ar 8000 -ac 1 -acodec pcm_s16le output.wav

# 批量转换
for file in *.mp3; do
  ffmpeg -i "$file" -ar 8000 -ac 1 -acodec pcm_s16le "${file%.mp3}.wav"
done
```

### 常用音频示例
```bash
audio_files/
├── welcome.wav        # 欢迎语 (自动播放)
├── menu.wav           # 主菜单
├── option1.wav        # 选项1说明
├── option2.wav        # 选项2说明
├── please_wait.wav    # 请稍候
├── thank_you.wav      # 感谢语
├── goodbye.wav        # 再见
└── error.wav          # 错误提示
```

---

## 实际使用示例

### 示例1: IVR菜单系统（音频队列模式）

```python
#!/usr/bin/env python3
"""
IVR示例: 自动播放菜单
"""
import requests
import time

API_BASE = "http://localhost:8088/api"

# 1. 拨打电话
response = requests.post(f"{API_BASE}/call", 
                         json={"phone_number": "82121065486"})
print(response.json())

# 2. 等待接通
time.sleep(5)

# 3. 添加菜单音频
menu_files = ["menu.wav", "option1.wav", "option2.wav", "goodbye.wav"]
for audio_file in menu_files:
    response = requests.post(f"{API_BASE}/add_audio", 
                            json={"filename": audio_file})
    print(f"添加: {audio_file} - {response.json()}")
    time.sleep(0.5)

# 4. 系统会自动按顺序播放
# 等待通话结束...
time.sleep(60)

# 5. 挂断
response = requests.post(f"{API_BASE}/hangup")
print(response.json())
```

### 示例2: 紧急通知（立即播放）

```python
#!/usr/bin/env python3
"""
紧急通知示例: 打断当前播放
"""
import requests

API_BASE = "http://localhost:8088/api"

# 立即播放紧急通知
response = requests.post(f"{API_BASE}/play_now", 
                         json={"filename": "urgent_notice.wav"})
print(response.json())
```

### 示例3: 麦克风实时通话

```bash
# 启动麦克风模式
python3 sip_two_way_voice.py --mode microphone

# 通过Web界面拨号
# 接通后直接对着麦克风说话
# 对方声音从扬声器输出
```

---

## 底层技术原理

### PJSIP 音频桥接 (Conference Bridge)

```
                    Conference Bridge (Slot管理)
                    ┌─────────────────────────┐
                    │                         │
    Slot 0          │      Audio Mixer        │
    (本地设备)  ←──→ │                         │
                    │                         │
    Slot 1          │                         │
    (呼叫)      ←──→ │     智能混音           │
                    │     回声消除           │
    Slot 2          │     音量控制           │
    (播放器)    ←──→ │                         │
                    │                         │
    Slot 3          │                         │
    (录音器)    ←──→ │                         │
                    │                         │
                    └─────────────────────────┘
```

### 连接配置对比

#### 麦克风模式
```python
pj.Lib.instance().conf_connect(call_slot, 0)  # 对方 → 扬声器
pj.Lib.instance().conf_connect(0, call_slot)  # 麦克风 → 对方
```

#### 音频队列模式
```python
pj.Lib.instance().conf_connect(call_slot, 0)        # 对方 → 扬声器
pj.Lib.instance().conf_connect(player_slot, call_slot)  # 播放器 → 对方
```

#### 录音连接
```python
pj.Lib.instance().conf_connect(call_slot, recorder_slot)  # 对方 → 录音
pj.Lib.instance().conf_connect(0, recorder_slot)          # 本地 → 录音
```

---

## 常见问题

### Q1: 音频队列模式下听不到对方声音怎么办？

**A:** 默认情况下，服务器模式(null音频设备)不会输出声音，这是正常的。如果需要听到对方声音用于调试：

```python
# 在启动时不设置null设备
# 修改代码: 注释掉 self.lib.set_null_snd_dev()
```

### Q2: 麦克风模式启动失败？

**A:** 检查音频设备：
```bash
# 列出可用音频设备
arecord -l   # 录音设备
aplay -l     # 播放设备

# 如果是服务器，安装虚拟音频设备
sudo apt-get install pulseaudio
```

### Q3: 音频播放没有声音？

**A:** 检查清单：
1. 确认音频文件存在: `ls audio_files/`
2. 检查音频格式: `file audio_files/your_file.wav`
3. 测试播放: `aplay audio_files/your_file.wav`
4. 确认采样率: 推荐 8000Hz

### Q4: 如何实现按键选择菜单？

**A:** 需要添加DTMF检测：
```python
# 在CallCallback中添加
def on_dtmf_digit(self, digits):
    if digits == '1':
        self.play_audio_file('option1.wav')
    elif digits == '2':
        self.play_audio_file('option2.wav')
```

### Q5: 可以同时进行多个呼叫吗？

**A:** 当前版本只支持单个呼叫。如需多路呼叫，需要：
1. 创建多个账户实例
2. 分别管理各自的音频桥接
3. 使用不同的端口

### Q6: 录音文件在哪里？

**A:** 
```bash
# 录音保存位置
/home/henry/pjproject/recordings/

# 文件命名格式
call_20251107_143025.wav  # call_日期_时间.wav
```

### Q7: 如何添加TTS（文字转语音）？

**A:** 可以集成在线TTS服务：
```python
import requests

def text_to_speech(text):
    # 调用TTS API
    response = requests.post('https://tts-api.example.com/convert', 
                            json={'text': text})
    
    # 保存为音频文件
    with open('temp_tts.wav', 'wb') as f:
        f.write(response.content)
    
    # 播放
    voice_system.play_audio_now('temp_tts.wav')
```

---

## 生产环境部署建议

### 1. 使用systemd服务
```bash
# /etc/systemd/system/voice-system.service
[Unit]
Description=Two-Way Voice System
After=network.target

[Service]
Type=simple
User=henry
WorkingDirectory=/home/henry/pjproject
ExecStart=/usr/bin/python3 sip_two_way_voice.py --mode audio_queue
Restart=always

[Install]
WantedBy=multi-user.target
```

### 2. 反向代理（Nginx）
```nginx
server {
    listen 80;
    server_name voice.example.com;
    
    location / {
        proxy_pass http://localhost:8088;
        proxy_set_header Host $host;
    }
}
```

### 3. 日志管理
```python
# 添加日志记录
import logging

logging.basicConfig(
    filename='/var/log/voice_system.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
```

### 4. 音频文件CDN
```bash
# 如果音频文件很大，使用CDN
# 在播放前先下载到本地
wget https://cdn.example.com/audio/menu.wav -O audio_files/menu.wav
```

---

## 性能优化

### 1. 音频预加载
```python
# 启动时预加载常用音频
preload_files = ['welcome.wav', 'menu.wav', 'goodbye.wav']
for filename in preload_files:
    audio_path = os.path.join(CONFIG['audio_dir'], filename)
    # 验证文件存在
    assert os.path.exists(audio_path)
```

### 2. 音频压缩
```bash
# 使用更小的采样率降低带宽
ffmpeg -i input.wav -ar 8000 -b:a 64k output.wav
```

### 3. 并发呼叫
```python
# 使用多进程处理多个呼叫
from multiprocessing import Process

for phone in phone_list:
    p = Process(target=make_call_worker, args=(phone,))
    p.start()
```

---

## 总结对比

| 特性 | 麦克风模式 | 音频队列模式 | 混合模式 |
|------|-----------|-------------|---------|
| 实时互动 | ✅ 是 | ❌ 否 | ❌ 否 |
| 服务器友好 | ❌ 否 | ✅ 是 | ✅ 是 |
| 音频质量 | 取决于设备 | 可控(预录) | 可控(预录) |
| 录制对方 | ✅ 是 | ✅ 是 | ✅ 是 |
| 发送音频 | 麦克风 | 预录文件 | 预录文件 |
| 典型场景 | 人工客服 | 自动IVR | 语音留言 |

---

## 下一步增强计划

- [ ] DTMF按键检测（菜单选择）
- [ ] 语音识别集成（ASR）
- [ ] 文字转语音（TTS）
- [ ] 多路并发呼叫
- [ ] WebSocket实时状态推送
- [ ] 呼叫统计和报表

---

## 支持

如有问题，请查看：
- `/home/henry/pjproject/sip_two_way_voice.py` - 完整源代码
- PJSIP官方文档: https://www.pjsip.org/docs/book-latest/html/
- 项目录音目录: `/home/henry/pjproject/recordings/`

---

**享受双向语音通信！** 🎙️📞

# 🤖 AI智能对话系统

基于PJSIP + faster-whisper + 阿里云通义千问TTS + OpenAI GPT的完整AI语音对话方案

**核心技术栈**：
- 📞 **SIP通话**: PJSIP
- 🎤 **语音识别**: faster-whisper (ASR)
- 🤖 **AI对话**: OpenAI GPT-3.5-turbo
- 🔊 **语音合成**: 阿里云DashScope (通义千问TTS)
- 🎯 **语音检测**: WebRTC VAD
- 💾 **通话录音**: 双向录制

---

## 🔑 配置信息

### API密钥配置

在启动前，请设置以下环境变量：

```bash
# OpenAI API Key
export OPENAI_API_KEY="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"

# 阿里云DashScope API Key（可选，已在代码中配置）
export DASHSCOPE_API_KEY="sk-ebf86b67058945fa827863a3742df0b0"
```

### SIP服务器配置（印度尼西亚线路）

```yaml
服务器地址: 147.139.205.88
SIP端口: 5060
主叫号码: 6281479242434
被叫前缀: 13462
拨号格式: 13462 + 目标号码
```

**示例**：拨打印尼手机号 `81234567890`
- 完整号码：`1346281234567890`
- SIP URI: `sip:1346281234567890@147.139.205.88:5060`

---

## 🚀 快速开始

### 推荐：使用完整AI对话系统

**主文件**: `sip_ai_with_webrtc_vad.py` ⭐

```bash
cd /home/henry/pjproject

# 1. 设置API Key
export OPENAI_API_KEY="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"

# 2. 启动AI对话系统
python3 sip_ai_with_webrtc_vad.py

# 3. 在浏览器打开控制界面
http://localhost:8090
```

### 备选：简单拨号测试（无AI）

```bash
# 直接拨打测试（60秒超时）
python3 sip_test_call_indonesia.py 81234567890 60
```

---

## 💡 为什么要预下载模型？

### 问题
之前启动时下载模型会导致：
- ❌ 启动等待2-3分钟
- ❌ 页面打不开（模型下载中）
- ❌ 用户体验差

### 解决方案
现在通过 `complete_setup.sh`：
- ✅ 提前下载好所有模型
- ✅ 启动只需5-10秒
- ✅ 打开页面立即可用

---

## 📋 两种安装方式对比

### 方式A：完整安装（推荐）⭐
```bash
./complete_setup.sh    # 第一次运行
./start_now.sh         # 以后每次启动
```

**优点**：
- ✅ 模型提前下载
- ✅ 启动超快
- ✅ 体验最好

---

### 方式B：按需下载（不推荐）
```bash
python3 sip_ai_conversation.py  # 直接启动
```

**缺点**：
- ⚠️ 首次启动等待2-3分钟
- ⚠️ 页面暂时打不开
- ⚠️ 体验较差

---

## 🎯 系统功能

### 核心能力
- 🎤 **实时语音识别** (ASR - faster-whisper)
- 🤖 **AI智能对话** (GPT-3.5-turbo)
- 🔊 **自然语音合成** (TTS - Edge TTS)
- 🇮🇩 **印尼语优化**

### 性能指标
- ⚡ **延迟**: 3-5秒（可优化到<2秒）
- 💰 **成本**: ~$0.01/分钟
- 🎯 **准确率**: 高（base模型）

---

## 📁 重要文件说明

### 主要系统文件

#### 1. 完整AI对话系统（推荐）⭐
**文件**: `sip_ai_with_webrtc_vad.py`

**功能**:
- ✅ ASR语音识别（faster-whisper）
- ✅ OpenAI GPT-3.5对话
- ✅ 阿里云DashScope TTS（通义千问）
- ✅ WebRTC VAD实时语音检测
- ✅ 双向录音（客户+AI）
- ✅ Web控制界面（端口8090）

**使用场景**: 完整的AI语音对话服务

---

#### 2. 基础AI对话（备选）
**文件**: `sip_ai_conversation.py`

**功能**:
- ✅ ASR + AI对话
- ✅ Edge TTS（免费但功能较少）
- ⚠️ 不支持DashScope TTS

**使用场景**: 测试或备选方案

---

#### 3. 简单拨号测试
**文件**: `sip_test_call_indonesia.py`

**功能**:
- ✅ 基础SIP拨号
- ✅ 音频设备检测
- ✅ 通话状态显示
- ❌ 无AI功能
- ❌ 无录音

**使用场景**: 测试SIP连接和音频设备

---

### 测试工具

- `test_alibaba_tts.py` - 测试阿里云TTS（印尼语发音人indah）
- `test_alibaba_asr.py` - 测试阿里云ASR
- `test_call_safe.py` - 安全拨号测试（修复call_id问题）

### 文档

- `README.md` - 本文档 ⭐
- `AI_CONVERSATION_SYSTEM_README.md` - 完整系统配置指南 ⭐⭐⭐
- `ALIBABA_NLS_TEST_RESULTS.md` - 阿里云NLS测试结果
- `ALIBABA_NLS_WEBSOCKET_SUPPORT.md` - WebSocket支持说明
- `CALL_ID_ASSERTION_FIX.md` - Call ID问题修复文档

---

## 🔧 系统配置

### 主配置（`sip_ai_with_webrtc_vad.py`）

```python
CONFIG = {
    # SIP配置
    'server': '147.139.205.88',
    'port': 5060,
    'caller_number': '6281479242434',
    'prefix': '13462',
    
    # 目录配置（实际路径）
    'audio_dir': '/home/henry/pjproject/audio_files',
    'recordings_dir': '/home/henry/pjproject/recordings',
    'temp_dir': '/home/henry/pjproject/temp_audio',
    
    # Web API配置
    'api_host': '0.0.0.0',
    'api_port': 8090,
    
    # OpenAI配置
    'openai_api_key': os.getenv('OPENAI_API_KEY', ''),
    'ai_model': 'gpt-3.5-turbo',
    
    # ASR配置（faster-whisper）
    'whisper_model': 'base',        # tiny/base/small/medium/large-v3
    'whisper_device': 'cpu',        # cpu/cuda（有GPU可改为cuda）
    'whisper_compute_type': 'int8', # int8/float16/float32
    
    # TTS配置（备用Edge TTS）
    'tts_voice': 'id-ID-ArdiNeural',  # 印尼语男声
    
    # WebRTC VAD配置
    'vad_aggressiveness': 2,         # 0-3，3最激进
    'vad_frame_duration': 30,        # ms，可选10/20/30
    'vad_silence_frames': 20,        # 连续静音帧数判定句子结束
    'vad_min_speech_frames': 5,      # 最少语音帧数
}
```

### DashScope TTS配置

**API Key**（已在代码中配置）:
```python
DASHSCOPE_API_KEY = "sk-ebf86b67058945fa827863a3742df0b0"
```

**支持的印尼语发音人**:
- `sambert-zhichu-v1` - 中文男声（示例）
- 更多印尼语发音人请参考阿里云文档

---

## 📊 完整对话流程

```
1. 启动系统
   python3 sip_ai_with_webrtc_vad.py
   ↓
2. 访问Web界面
   http://localhost:8090
   ↓
3. 输入电话号码（如：81234567890）
   ↓
4. 点击"拨打电话"
   ↓
5. 电话接通，系统开始双向录音
   ↓
6. WebRTC VAD实时检测用户说话
   ↓
7. 检测到完整句子后自动处理：
   7.1 ASR识别语音 → 文字 (1-2秒)
   7.2 发送到OpenAI GPT → AI回复 (1秒)
   7.3 DashScope TTS合成 → 语音 (1-2秒)
   7.4 播放给用户
   ↓
8. 重复步骤6-7，持续对话
   ↓
9. 通话结束，保存完整录音
   位置：/home/henry/pjproject/recordings/
   格式：call_YYYYMMDD_HHMMSS.wav
```

**总延迟**: 3-5秒（可优化至2-3秒）

---

## 💰 成本分析

### 每月成本（1000分钟通话）

| 项目 | 成本 | 说明 |
|------|------|------|
| ASR (faster-whisper) | 免费 | 本地运行 |
| TTS (DashScope) | ~$2-5 | 阿里云按量计费 |
| AI (GPT-3.5-turbo) | ~$5-10 | OpenAI按token计费 |
| SIP通话费 | ~$10-20 | 取决于线路 |
| 服务器 | ~$10 | VPS托管 |
| **总计** | **~$27-45/月** | 实际使用量计费 |

**优势**:
- ✅ 按实际使用量付费
- ✅ 无最低消费
- ✅ DashScope TTS质量优于免费方案
- ✅ 对比商业方案节省60-80%

---

## 🐛 常见问题排查

### Q1: Call ID断言失败崩溃
**错误**: `Assertion 'call_id>=0 && call_id<(int)pjsua_var.ua_cfg.max_calls' failed`

**原因**: 多线程访问已失效的呼叫对象

**解决**: 
- ✅ 使用修复后的 `sip_test_call_indonesia.py`
- ✅ 或使用 `test_call_safe.py`
- 📖 详见：`CALL_ID_ASSERTION_FIX.md`

### Q2: OpenAI API错误
**错误**: `AuthenticationError` 或 `RateLimitError`

**检查**:
```bash
# 验证API Key
echo $OPENAI_API_KEY

# 重新设置
export OPENAI_API_KEY="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"
```

### Q3: DashScope TTS失败
**错误**: TTS合成失败

**原因**:
1. API Key错误
2. 网络连接问题
3. 配额用完

**解决**:
- 系统会自动降级到Edge TTS
- 检查阿里云账户余额
- 查看配额使用情况

### Q4: 音频设备未找到
**错误**: 无法找到音频设备

**检查**:
```bash
# 检查ALSA设备
aplay -l
arecord -l

# 检查PulseAudio
pactl list sinks short
pactl list sources short
```

**解决**:
- 确保音频设备已连接
- 重启PulseAudio: `pulseaudio -k && pulseaudio -D`

### Q5: 录音文件为空
**问题**: 录音文件存在但大小为0

**原因**: 音频设备或桥接未正确连接

**检查**:
1. 呼叫是否成功接通
2. 媒体通道是否激活
3. 录音器是否正确创建

### Q6: Whisper模型下载慢
**问题**: 首次运行时模型下载很慢

**解决**:
```bash
# 预先下载模型
python3 download_models.py
```

### Q7: 页面无法访问
**问题**: `http://localhost:8090` 打不开

**检查**:
```bash
# 检查进程是否运行
ps aux | grep sip_ai

# 检查端口占用
netstat -tuln | grep 8090

# 查看系统日志
```

---

## 📚 完整文档索引

### 核心文档
1. **README.md** - 本文档，快速开始指南 ⭐
2. **AI_CONVERSATION_SYSTEM_README.md** - 完整系统配置和使用指南 ⭐⭐⭐

### 测试和功能文档
3. **ALIBABA_NLS_TEST_RESULTS.md** - 阿里云NLS测试结果
   - TTS测试（印尼语发音人indah）
   - ASR测试
   - 配置示例

4. **ALIBABA_NLS_WEBSOCKET_SUPPORT.md** - WebSocket支持说明
   - WebSocket协议详解
   - 连接流程
   - 内网访问配置

### 问题修复文档
5. **CALL_ID_ASSERTION_FIX.md** - Call ID断言失败问题修复
   - 问题原因分析
   - 修复方案
   - 代码对比

### 其他文档
6. **AI_CONVERSATION_GUIDE.md** - AI对话系统使用指南
7. **FINAL_SETUP.md** - 最终配置总结
8. **PROJECT_SUMMARY.md** - 项目总结

---

## ✅ 推荐使用流程

### 方案A：完整AI对话系统（推荐）⭐

```bash
cd /home/henry/pjproject

# 1. 设置环境变量
export OPENAI_API_KEY="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"

# 可选：设置DashScope Key（已在代码中配置）
export DASHSCOPE_API_KEY="sk-ebf86b67058945fa827863a3742df0b0"

# 2. 启动系统
python3 sip_ai_with_webrtc_vad.py

# 3. 访问Web界面
# 浏览器打开：http://localhost:8090
```

**功能**：
- ✅ 完整的ASR + AI + TTS
- ✅ DashScope TTS（通义千问）
- ✅ WebRTC VAD实时检测
- ✅ 双向录音
- ✅ Web控制界面

---

### 方案B：简单拨号测试

```bash
cd /home/henry/pjproject

# 直接拨打电话（无AI）
python3 sip_test_call_indonesia.py 81234567890 60

# 参数：
# 81234567890 - 目标号码
# 60 - 超时秒数
```

**功能**：
- ✅ 基础SIP拨号
- ✅ 音频设备检测
- ❌ 无AI功能
- ❌ 无录音

---

## 🎯 快速测试

### 测试阿里云服务

```bash
# 测试TTS（印尼语）
python3 test_alibaba_tts.py

# 测试ASR
python3 test_alibaba_asr.py
```

### 查看录音文件

```bash
# 查看所有录音
ls -lh /home/henry/pjproject/recordings/

# 播放最新录音
ffplay /home/henry/pjproject/recordings/call_*.wav
```

---

## 🎉 开始使用

### 推荐：完整AI对话

```bash
cd /home/henry/pjproject

# 设置API Key
export OPENAI_API_KEY="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"

# 启动系统
python3 sip_ai_with_webrtc_vad.py
```

**访问**: **http://localhost:8090**

享受AI语音对话！🚀🤖

---

## 📞 技术支持

- 📖 **详细文档**: 查看 `AI_CONVERSATION_SYSTEM_README.md`
- 🐛 **问题修复**: 查看 `CALL_ID_ASSERTION_FIX.md`
- 🔧 **配置指南**: 查看各个专题文档

**项目路径**: `/home/henry/pjproject/`

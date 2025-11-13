# AI智能对话系统使用指南

## 📋 系统概述

完整的SIP + AI对话系统，支持：
- ✅ **ASR语音识别** - faster-whisper
- ✅ **AI智能对话** - OpenAI GPT-3.5-turbo
- ✅ **语音合成TTS** - 阿里云通义千问 (DashScope)
- ✅ **实时VAD检测** - WebRTC VAD
- ✅ **双向录音** - 完整通话录制

## 🎯 主要文件

### 1. 完整AI对话系统（推荐）
**文件**: `sip_ai_with_webrtc_vad.py`

**功能**:
- ASR语音识别（faster-whisper）
- OpenAI GPT-3.5对话
- 阿里云DashScope TTS（通义千问）
- WebRTC VAD实时语音检测
- 双向录音（客户+AI）

### 2. 基础版AI对话
**文件**: `sip_ai_conversation.py`

**功能**:
- 使用Edge TTS（免费但功能较少）
- 其他功能类似

### 3. 简单拨号测试
**文件**: `sip_test_call_indonesia.py`

**功能**:
- 基础拨号测试
- 无AI功能
- 无录音

## 🔑 配置信息

### API密钥配置

#### OpenAI API Key
```
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
```

#### 阿里云DashScope API Key
```
sk-ebf86b67058945fa827863a3742df0b0
```

### SIP服务器配置

#### 印度尼西亚线路
```yaml
服务器地址: 147.139.205.88
SIP端口: 5060
主叫号码: 6281479242434
被叫前缀: 13462
拨号格式: 13462 + 目标号码
```

示例：拨打印尼号码 `81234567890`
- 完整被叫号码：`1346281234567890`
- SIP URI: `sip:1346281234567890@147.139.205.88:5060`

## 📁 目录结构

### 项目根目录
```
/home/henry/pjproject/
```

### 重要目录

#### 1. 音频文件目录
```
/home/henry/pjproject/audio_files/
```
用途：存储AI回复的音频文件

#### 2. 录音目录
```
/home/henry/pjproject/recordings/
```
用途：存储完整通话录音
格式：`call_YYYYMMDD_HHMMSS.wav`

#### 3. 临时文件目录
```
/home/henry/pjproject/temp_audio/
```
用途：存储临时音频处理文件

#### 4. 阿里云NLS SDK
```
/home/henry/pjproject/alibabacloud-nls-python-sdk/
```
用途：阿里云语音服务Python SDK

## 🚀 快速开始

### 方法1：命令行启动（推荐）

#### 设置环境变量
```bash
cd /home/henry/pjproject

# 设置OpenAI API Key
export OPENAI_API_KEY="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"

# 设置DashScope API Key（已在代码中硬编码，可选）
export DASHSCOPE_API_KEY="sk-ebf86b67058945fa827863a3742df0b0"
```

#### 启动AI对话系统
```bash
# 启动完整AI对话系统
python3 sip_ai_with_webrtc_vad.py
```

#### 通过Web界面控制
```bash
# 在浏览器打开
http://localhost:8090
```

### 方法2：直接测试拨号

```bash
# 简单拨号测试（无AI）
python3 sip_test_call_indonesia.py 81234567890 60

# 参数说明：
# 81234567890 - 目标号码（印尼手机号）
# 60 - 超时时间（秒）
```

## 🔧 系统配置详解

### AI对话系统配置
文件：`sip_ai_with_webrtc_vad.py`

```python
CONFIG = {
    # SIP配置
    'server': '147.139.205.88',
    'port': 5060,
    'caller_number': '6281479242434',
    'prefix': '13462',
    'log_level': 3,
    
    # 目录配置
    'audio_dir': '/home/henry/pjproject/audio_files',
    'recordings_dir': '/home/henry/pjproject/recordings',
    'temp_dir': '/home/henry/pjproject/temp_audio',
    
    # API配置
    'api_host': '0.0.0.0',
    'api_port': 8090,
    
    # OpenAI配置
    'openai_api_key': os.getenv('OPENAI_API_KEY', ''),
    'ai_model': 'gpt-3.5-turbo',
    
    # ASR配置（faster-whisper）
    'whisper_model': 'base',        # tiny/base/small/medium/large-v3
    'whisper_device': 'cpu',        # cpu/cuda
    'whisper_compute_type': 'int8', # int8/float16/float32
    
    # TTS配置（备用Edge TTS）
    'tts_voice': 'id-ID-ArdiNeural', # 印尼语男声
    
    # WebRTC VAD配置
    'vad_aggressiveness': 2,         # 0-3，3最激进
    'vad_frame_duration': 30,        # ms, 可选10/20/30
    'vad_silence_frames': 20,        # 连续静音帧数判定句子结束
    'vad_min_speech_frames': 5,      # 最少语音帧数
}
```

### DashScope TTS配置
文件位置：`sip_ai_with_webrtc_vad.py` Line 241-264

```python
# DashScope API Key（已硬编码在代码中）
API_KEY = 'sk-ebf86b67058945fa827863a3742df0b0'

# 支持的声音模型
voice_models = [
    'sambert-zhichu-v1',      # 中文
    'sambert-zhimiao-v1',     # 中文女声
    'sambert-zhiyan-v1',      # 中文女声
    # 更多可在阿里云文档查询
]
```

## 📊 工作流程

### 完整对话流程

```
1. 用户拨打电话
   ↓
2. 系统接通并开始双向录音
   ↓
3. WebRTC VAD实时检测用户说话
   ↓
4. 检测到完整句子后：
   4.1 ASR识别语音 → 文字
   4.2 发送到OpenAI GPT → AI回复
   4.3 DashScope TTS合成 → 语音
   4.4 播放给用户
   ↓
5. 循环3-4，持续对话
   ↓
6. 通话结束，保存完整录音
```

### 录音文件命名规则

```
格式: call_YYYYMMDD_HHMMSS.wav
示例: call_20231113_143052.wav

位置: /home/henry/pjproject/recordings/
```

## 🎮 Web控制界面

### 访问地址
```
http://localhost:8090
```

### 可用功能
- ✅ 拨打电话
- ✅ 挂断电话
- ✅ 查看通话状态
- ✅ 查看实时日志
- ✅ 控制静音
- ✅ 查看录音状态

### API接口

#### 拨打电话
```bash
curl -X POST http://localhost:8090/api/call/make \
  -H "Content-Type: application/json" \
  -d '{"destination": "81234567890"}'
```

#### 挂断电话
```bash
curl -X POST http://localhost:8090/api/call/hangup
```

#### 查看状态
```bash
curl http://localhost:8090/api/status
```

## 🔍 测试工具

### 1. 测试阿里云TTS
```bash
cd /home/henry/pjproject
python3 test_alibaba_tts.py
```

### 2. 测试阿里云ASR
```bash
python3 test_alibaba_asr.py
```

### 3. 安全拨号测试
```bash
python3 test_call_safe.py 81234567890 30
```

## 📦 依赖安装

### 必需的Python包

```bash
# PJSUA (SIP库)
# 已编译在项目中

# AI相关
pip3 install openai
pip3 install dashscope

# ASR相关
pip3 install faster-whisper

# VAD相关
pip3 install webrtcvad

# 音频处理
pip3 install numpy
pip3 install wave

# 阿里云NLS SDK
cd /home/henry/pjproject/alibabacloud-nls-python-sdk
pip3 install -r requirements.txt
pip3 install .
```

### 系统依赖

```bash
# FFmpeg（音频格式转换）
sudo apt-get install ffmpeg

# ALSA音频库
sudo apt-get install libasound2-dev

# PulseAudio
sudo apt-get install pulseaudio
```

## 🐛 常见问题

### 1. Call ID断言失败
**错误**: `Assertion 'call_id>=0 && call_id<(int)pjsua_var.ua_cfg.max_calls' failed`

**解决**: 使用修复后的版本
- ✅ `sip_test_call_indonesia.py` - 已修复
- ✅ `test_call_safe.py` - 安全版本

### 2. OpenAI API错误
**错误**: `AuthenticationError` 或 `RateLimitError`

**检查**:
```bash
# 验证API Key是否正确设置
echo $OPENAI_API_KEY

# 重新设置
export OPENAI_API_KEY="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"
```

### 3. DashScope TTS失败
**错误**: TTS合成失败

**解决**:
1. 检查API Key是否正确
2. 检查网络连接
3. 查看配额是否用完
4. 系统会自动降级到Edge TTS

### 4. 音频设备问题
**错误**: 无法找到音频设备

**解决**:
```bash
# 检查音频设备
aplay -l
arecord -l

# 检查PulseAudio
pactl list sinks short
pactl list sources short
```

### 5. 录音文件为空
**问题**: 录音文件存在但大小为0

**原因**: 音频设备未正确连接

**解决**: 检查音频桥接配置和设备连接

## 📝 日志说明

### 日志级别
```python
LOG_LEVEL = 3  # 0=致命, 1=错误, 2=警告, 3=信息, 4=调试, 5=详细
```

### 关键日志标记
```
[ASR]   - 语音识别相关
[TTS]   - 语音合成相关
[AI]    - AI对话相关
[VAD]   - 语音检测相关
[录音]   - 录音相关
[媒体]   - 音频通道相关
[状态]   - 呼叫状态相关
```

## 📞 联系支持

### 阿里云服务
- DashScope文档: https://help.aliyun.com/zh/model-studio/
- NLS文档: https://help.aliyun.com/zh/isi/

### OpenAI服务
- API文档: https://platform.openai.com/docs/
- 状态页: https://status.openai.com/

## 🔐 安全注意事项

### API密钥保护

⚠️ **重要**: 不要将API密钥提交到Git仓库

**最佳实践**:
```bash
# 使用环境变量
export OPENAI_API_KEY="your-key"
export DASHSCOPE_API_KEY="your-key"

# 或使用 .env 文件（记得添加到.gitignore）
echo "OPENAI_API_KEY=your-key" > .env
echo "DASHSCOPE_API_KEY=your-key" >> .env
```

### 录音文件管理

录音文件包含用户隐私信息，请妥善保管：
- 定期清理旧录音
- 限制访问权限
- 符合当地法律法规

## 📈 性能优化

### 提升识别速度
```python
# 使用更小的Whisper模型
'whisper_model': 'tiny'  # 最快，准确度较低
'whisper_model': 'base'  # 平衡
'whisper_model': 'small' # 较准确，较慢
```

### 启用GPU加速
```python
# 需要CUDA环境
'whisper_device': 'cuda'
'whisper_compute_type': 'float16'
```

### 调整VAD灵敏度
```python
# 更快响应（可能误触发）
'vad_silence_frames': 10

# 更稳定（延迟更高）
'vad_silence_frames': 30
```

## 🎯 下一步

1. **测试基础拨号**
   ```bash
   python3 sip_test_call_indonesia.py 81234567890
   ```

2. **测试AI对话**
   ```bash
   export OPENAI_API_KEY="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"
   python3 sip_ai_with_webrtc_vad.py
   ```

3. **在浏览器打开控制界面**
   ```
   http://localhost:8090
   ```

4. **查看录音文件**
   ```bash
   ls -lh /home/henry/pjproject/recordings/
   ```

---

**文档版本**: 1.0  
**最后更新**: 2025-11-13  
**维护者**: Henry

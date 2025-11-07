# AI智能对话系统 使用指南

## 🎯 系统概述

这是一个**完全免费**的AI智能对话系统，能够实现：
- 📞 自动接听电话
- 🎤 识别对方语音 (ASR)
- 🤖 AI智能回复
- 🔊 语音播报给对方 (TTS)
- 🇮🇩 **印尼语优化**

### 免费方案配置

| 组件 | 技术 | 成本 | 特点 |
|------|------|------|------|
| ASR | faster-whisper | 免费 | GPU加速，比Whisper快4倍 |
| TTS | Edge TTS | 免费 | 微软服务，质量好，支持印尼语 |
| AI | GPT-3.5-turbo | ~$0.002/1K tokens | 便宜快速 |

**预估成本**: 每分钟通话 **$0.01-0.05**

---

## 🚀 快速开始

### 1. 安装依赖

```bash
cd /home/henry/pjproject

# 运行自动安装脚本
./install_ai_dependencies.sh
```

脚本会自动安装：
- ✅ ffmpeg (音频处理)
- ✅ faster-whisper (ASR)
- ✅ edge-tts (TTS)
- ✅ openai (AI)
- ✅ numpy (数据处理)

### 2. 配置 OpenAI API Key

```bash
# 方法1: 临时设置
export OPENAI_API_KEY='sk-your-key-here'

# 方法2: 永久设置 (推荐)
echo "export OPENAI_API_KEY='sk-your-key-here'" >> ~/.bashrc
source ~/.bashrc
```

**获取API Key**: https://platform.openai.com/api-keys

### 3. 启动系统

```bash
python3 sip_ai_conversation.py
```

成功启动后会看到：
```
✓ 传输: xxx.xxx.xxx.xxx:xxxxx
✓ 音频设备: null设备 (服务器模式)
✓ 账户已创建
✓ API服务器: http://localhost:8089

系统启动成功!
```

### 4. 访问控制面板

浏览器打开：
```
http://localhost:8089
```

或使用API：
```bash
# 发起呼叫
curl -X POST http://localhost:8089/api/call \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "82121065486"}'

# 挂断
curl -X POST http://localhost:8089/api/hangup

# 查询状态
curl -X POST http://localhost:8089/api/status
```

---

## 🔧 工作原理

### 完整对话流程

```
┌─────────────────────────────────────────────────────────────┐
│                     AI对话流程                               │
└─────────────────────────────────────────────────────────────┘

1️⃣  对方说话
    ↓
2️⃣  VAD检测语音活动
    ↓ (检测到静音1.5秒 → 句子结束)
3️⃣  音频片段保存为WAV
    ↓
4️⃣  faster-whisper ASR识别
    ↓ (约1-2秒)
    文本: "Halo, saya ingin bertanya..."
    ↓
5️⃣  GPT-3.5处理并生成回复
    ↓ (约1秒)
    回复: "Halo! Silakan, ada yang bisa saya bantu?"
    ↓
6️⃣  Edge TTS语音合成
    ↓ (约1-2秒)
7️⃣  播放给对方
    ↓
    对方听到AI回复

总延迟: 3-5秒
```

### 技术架构

```
┌─────────────────────────────────────────────────────┐
│                  PJSIP底层                          │
│  ┌──────────┐      Conference      ┌──────────┐    │
│  │ RTP接收  │ ───→   Bridge   ───→ │ RTP发送  │    │
│  └──────────┘         ↓             └──────────┘    │
│                   录音/播放                          │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│                  AI处理层                            │
│                                                      │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐      │
│  │   VAD    │ →  │   ASR    │ →  │   AI     │      │
│  │ 语音检测  │    │ 识别文本  │    │ 生成回复  │      │
│  └──────────┘    └──────────┘    └──────────┘      │
│                        ↓                             │
│                  ┌──────────┐                        │
│                  │   TTS    │                        │
│                  │ 语音合成  │                        │
│                  └──────────┘                        │
└─────────────────────────────────────────────────────┘
```

---

## ⚙️ 配置优化

### 配置文件位置
编辑 `sip_ai_conversation.py` 中的 `CONFIG` 字典

### 关键配置项

#### 1. Whisper模型选择
```python
'whisper_model': 'base',  # 可选: tiny/base/small/medium/large-v3
```

**对比**:
| 模型 | 大小 | 速度 | 准确率 | 推荐场景 |
|------|------|------|--------|---------|
| tiny | 75MB | 最快 | 较低 | 测试 |
| base | 142MB | 快 | 中等 | **生产推荐** |
| small | 466MB | 中 | 高 | 高质量需求 |
| medium | 1.5GB | 慢 | 很高 | 准确率优先 |

#### 2. GPU加速 (如果有GPU)
```python
'whisper_device': 'cuda',  # 改为cuda
'whisper_compute_type': 'float16',  # GPU推荐float16
```

速度提升：**2-5倍**

检查GPU:
```bash
nvidia-smi
```

#### 3. TTS语音选择
```python
'tts_voice': 'id-ID-ArdiNeural',  # 印尼语男声
```

**可选印尼语音**:
- `id-ID-ArdiNeural` - 男声（默认）
- `id-ID-GadisNeural` - 女声

查看所有语音：
```bash
edge-tts --list-voices | grep id-ID
```

#### 4. VAD灵敏度调整
```python
'vad_silence_duration': 1.5,  # 静音多久判定句子结束(秒)
'vad_speech_threshold': 0.02,  # 语音能量阈值(0-1)
```

- 降低 `vad_silence_duration`: 更快响应，但可能打断对方
- 提高 `vad_silence_duration`: 更完整句子，但延迟增加

#### 5. AI回复风格
编辑 `DialogueEngine.system_prompt`:
```python
self.system_prompt = """Anda adalah asisten virtual yang ramah.
Anda berbicara dalam bahasa Indonesia.
Jawaban Anda singkat (maksimal 2-3 kalimat).
[添加你的业务逻辑...]"""
```

---

## 📊 性能优化

### 1. 降低延迟 (目标: <2秒)

#### 使用GPU加速
```bash
# 安装CUDA支持的PyTorch
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# 修改配置
'whisper_device': 'cuda',
'whisper_compute_type': 'float16',
```

**效果**: ASR时间从 2秒 → 0.5秒

#### 使用更小的模型
```python
'whisper_model': 'tiny',  # 最快，但准确率低
```

**效果**: ASR时间 0.5秒，但可能识别错误

#### 缓存常用回复
```python
# 在 TTSEngine.__init__ 中添加
self.preload_cache = {
    'Halo': 'path/to/hello.wav',
    'Terima kasih': 'path/to/thanks.wav',
}
```

### 2. 提升准确率

#### 使用更大模型
```python
'whisper_model': 'small',  # 或 medium
```

#### 印尼语方言支持
```python
# 在 ASR transcribe 中指定方言
segments, info = self.model.transcribe(
    audio_file,
    language='id',
    initial_prompt="Ini adalah percakapan dalam bahasa Indonesia."
)
```

### 3. 降低成本

#### 使用GPT-3.5而非GPT-4
```python
'ai_model': 'gpt-3.5-turbo',  # $0.002/1K vs GPT-4 $0.03/1K
```

#### 限制回复长度
```python
response = openai.ChatCompletion.create(
    model=CONFIG['ai_model'],
    messages=messages,
    max_tokens=100,  # 减少tokens
)
```

#### 使用本地ASR（完全免费）
faster-whisper在本地运行，不产生费用

---

## 🎭 实际对话示例

### 示例1: 简单问答

```
👤 用户: "Halo, jam berapa sekarang?"
      (你好，现在几点？)
      
🔄 处理流程:
   [1/4] 音频保存 (0.1s)
   [2/4] ASR识别 (1.5s)
   [3/4] AI生成 (0.8s)
   [4/4] TTS合成 (1.2s)

🤖 AI: "Halo! Sekarang pukul 14:30."
      (你好！现在是14:30。)
      
总耗时: 3.6秒
```

### 示例2: 业务查询

```
👤 用户: "Saya ingin mengecek pesanan saya."
      (我想查询订单。)
      
🤖 AI: "Tentu! Silakan berikan nomor pesanan Anda."
      (当然！请提供您的订单号。)

👤 用户: "Nomor pesanan 1234567890."

🤖 AI: "Pesanan Anda sedang dalam pengiriman dan 
       akan tiba besok."
      (您的订单正在配送中，明天送达。)
```

### 示例3: 多轮对话

系统会记住上下文（最近10轮对话）：

```
👤: "Siapa nama presiden Indonesia?"
🤖: "Presiden Indonesia saat ini adalah Joko Widodo."

👤: "Kapan dia menjabat?"
🤖: "Beliau menjabat sejak tahun 2014."

👤: "Terima kasih!"
🤖: "Sama-sama! Ada yang bisa saya bantu lagi?"
```

---

## 🐛 故障排查

### 问题1: ASR识别不准确

**原因**:
- 模型太小
- 音频质量差
- 背景噪音大

**解决**:
```python
# 1. 使用更大模型
'whisper_model': 'small',

# 2. 启用降噪
# 在录音前添加降噪处理

# 3. 调整VAD参数
'vad_speech_threshold': 0.03,  # 提高阈值
```

### 问题2: TTS合成失败

**检查**:
```bash
# 测试Edge TTS
edge-tts --text "Halo" --voice id-ID-ArdiNeural --write-media test.mp3

# 检查ffmpeg
ffmpeg -version
```

**解决**:
```bash
# 重新安装
pip3 install edge-tts --upgrade
sudo apt-get install ffmpeg
```

### 问题3: AI回复太慢

**优化**:
```python
# 1. 减少max_tokens
max_tokens=80,  # 从150减到80

# 2. 使用流式API (高级)
stream=True,

# 3. 预判用户意图，预生成回复
```

### 问题4: OpenAI API错误

**常见错误**:
```
401 Unauthorized: API Key错误
429 Too Many Requests: 请求过多
500 Server Error: OpenAI服务器问题
```

**解决**:
```bash
# 检查API Key
echo $OPENAI_API_KEY

# 检查余额
# 访问: https://platform.openai.com/account/usage

# 添加重试机制
```

### 问题5: 内存占用过高

**Whisper模型占用内存**:
- tiny: ~500MB
- base: ~1GB
- small: ~2GB
- medium: ~5GB

**解决**:
```python
# 1. 使用更小模型
'whisper_model': 'tiny',

# 2. int8量化
'whisper_compute_type': 'int8',

# 3. 定期清理临时文件
import shutil
shutil.rmtree(CONFIG['temp_dir'])
os.makedirs(CONFIG['temp_dir'])
```

---

## 📈 监控和日志

### 实时监控

系统会打印详细日志：
```
[VAD] 检测到说话
[ASR] 识别完成: 'Halo, apa kabar?' (1.5秒)
[AI] 回复生成: 'Halo! Baik, terima kasih...' (0.8秒)
[TTS] 合成完成: 'Halo! Baik...' (1.2秒)
[播放] 正在播放给对方
```

### 保存录音

所有通话会自动录制：
```
/home/henry/pjproject/recordings/
└── ai_call_20251107_143025.wav
```

### 添加详细日志

```python
import logging

logging.basicConfig(
    filename='ai_conversation.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 在关键位置添加
logging.info(f"User said: {user_text}")
logging.info(f"AI replied: {ai_reply}")
```

---

## 🚀 高级功能

### 1. 添加DTMF按键检测

```python
def on_dtmf_digit(self, digits):
    """检测按键"""
    if digits == '1':
        # 用户按了1
        reply = "Anda memilih opsi 1."
        self.process_ai_reply(reply)
```

### 2. 集成数据库查询

```python
def get_response(self, user_text):
    # 检测关键词
    if 'pesanan' in user_text.lower():
        # 查询数据库
        order = self.query_order_database(user_text)
        return f"Pesanan Anda: {order}"
    
    # 否则使用AI
    return self.gpt_response(user_text)
```

### 3. 情感分析

```python
# 检测用户情绪
if self.is_angry(user_text):
    self.system_prompt = "用户生气了，请温和安抚。"
```

### 4. 多语言支持

```python
# 自动检测语言
detected_lang = self.detect_language(audio_file)

if detected_lang == 'id':
    self.tts_voice = 'id-ID-ArdiNeural'
elif detected_lang == 'en':
    self.tts_voice = 'en-US-GuyNeural'
```

---

## 📦 部署到生产环境

### 1. 使用Systemd服务

```bash
# /etc/systemd/system/ai-conversation.service
[Unit]
Description=AI Conversation System
After=network.target

[Service]
Type=simple
User=henry
WorkingDirectory=/home/henry/pjproject
Environment="OPENAI_API_KEY=your-key"
ExecStart=/usr/bin/python3 sip_ai_conversation.py
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl enable ai-conversation
sudo systemctl start ai-conversation
sudo systemctl status ai-conversation
```

### 2. Docker部署

```dockerfile
# Dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y ffmpeg

WORKDIR /app
COPY sip_ai_conversation.py .
RUN pip install faster-whisper edge-tts openai numpy pjsua

ENV OPENAI_API_KEY=""
EXPOSE 8089

CMD ["python3", "sip_ai_conversation.py"]
```

### 3. 负载均衡

多实例部署：
```bash
# 实例1: 端口8089
python3 sip_ai_conversation.py &

# 实例2: 修改配置端口8090
# CONFIG['api_port'] = 8090
python3 sip_ai_conversation.py &

# Nginx负载均衡
upstream ai_backend {
    server localhost:8089;
    server localhost:8090;
}
```

---

## 💰 成本分析

### 月度成本估算（1000分钟通话）

| 项目 | 用量 | 单价 | 月成本 |
|------|------|------|--------|
| ASR (faster-whisper) | 1000分钟 | 免费 | $0 |
| TTS (Edge TTS) | 1000分钟 | 免费 | $0 |
| AI (GPT-3.5) | ~500K tokens | $0.002/1K | $1 |
| 服务器 | 1台 | $5-20 | $10 |
| **总计** | | | **~$11/月** |

### 与商业方案对比

| 方案 | 月成本 (1000分钟) |
|------|------------------|
| 本方案 | $11 |
| Azure Speech + Azure OpenAI | $80+ |
| Google Dialogflow | $100+ |
| Twilio + AWS | $150+ |

**节省**: 85-95%

---

## 🔐 安全建议

### 1. 保护API Key
```bash
# 不要硬编码
# ❌ 错误
api_key = "sk-xxxxx"

# ✓ 正确
api_key = os.getenv('OPENAI_API_KEY')
```

### 2. 限制访问
```python
# 添加IP白名单
ALLOWED_IPS = ['127.0.0.1', '192.168.1.100']

def do_POST(self):
    client_ip = self.client_address[0]
    if client_ip not in ALLOWED_IPS:
        self.send_error(403, "Forbidden")
        return
```

### 3. 添加认证
```python
# HTTP Basic Auth
def check_auth(self, auth_header):
    if not auth_header:
        return False
    
    username, password = decode_base64(auth_header)
    return username == 'admin' and password == 'secure_pass'
```

---

## 📚 参考资源

- **faster-whisper**: https://github.com/SYSTRAN/faster-whisper
- **Edge TTS**: https://github.com/rany2/edge-tts
- **OpenAI API**: https://platform.openai.com/docs
- **PJSIP文档**: https://www.pjsip.org/docs/latest/pjsip/docs/html/

---

## 🎉 总结

你现在拥有一个：
- ✅ **完全免费**的ASR和TTS（只需AI API费用）
- ✅ **印尼语优化**，识别准确
- ✅ **低延迟**（3-5秒）
- ✅ **易于部署**，无需复杂配置
- ✅ **成本极低**（~$11/月处理1000分钟）

**开始使用**:
```bash
./install_ai_dependencies.sh
export OPENAI_API_KEY='your-key'
python3 sip_ai_conversation.py
```

祝你使用愉快！🚀🤖

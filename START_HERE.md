# 🚀 AI智能对话系统 - 立即开始

## ✅ 已完成的配置

- ✅ OpenAI API Key 已设置并测试通过
- ✅ 所有Python依赖已安装
- ✅ Edge TTS 可用（印尼语音：2个）
- ✅ faster-whisper 正在准备（首次下载模型）

## 🎯 立即启动

### 方法1: 快速启动（推荐）

```bash
cd /home/henry/pjproject
./quick_start_ai_conversation.sh
```

### 方法2: 直接启动

```bash
cd /home/henry/pjproject
export OPENAI_API_KEY='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'
python3 sip_ai_conversation.py
```

## 🌐 访问控制面板

启动后访问：
```
http://localhost:8089
```

或者如果从外部访问：
```
http://你的服务器IP:8089
```

## 📞 使用流程

1. **打开控制面板** → http://localhost:8089
2. **输入测试号码** → 例如: 82121065486
3. **点击"开始AI对话"**
4. **等待接通** → 对方接听后开始对话
5. **AI自动工作**:
   - 对方说话 → ASR识别
   - AI生成回复 → TTS合成
   - 自动播放给对方

## 🎭 对话示例

```
对方: "Halo, saya ingin bertanya tentang pesanan"
      (你好，我想询问订单)

AI:   "Halo! Tentu, silakan berikan nomor pesanan Anda."
      (你好！当然，请提供您的订单号)

对方: "Nomor pesanan 1234567890"

AI:   "Terima kasih! Saya akan mengecek pesanan Anda."
      (谢谢！我会查询您的订单)
```

## ⚙️ 系统配置

当前配置（在 `sip_ai_conversation.py` 中）：

```python
# ASR配置
'whisper_model': 'base',        # 推荐：准确率和速度平衡
'whisper_device': 'cpu',        # 如有GPU可改为'cuda'

# TTS配置  
'tts_voice': 'id-ID-ArdiNeural',  # 印尼语男声
# 可选: 'id-ID-GadisNeural'      # 印尼语女声

# AI配置
'ai_model': 'gpt-3.5-turbo',    # 快速且便宜

# VAD配置
'vad_silence_duration': 1.5,    # 1.5秒静音后处理
```

## 🔧 性能调优

### 降低延迟（<2秒）

```python
# 编辑 sip_ai_conversation.py
'whisper_model': 'tiny',           # 最快（牺牲准确率）
'vad_silence_duration': 1.0,       # 1秒即处理
```

### 提升准确率

```python
'whisper_model': 'small',          # 更准确（稍慢）
'vad_silence_duration': 2.0,       # 等待更完整句子
```

### 使用GPU加速（如果有）

```python
'whisper_device': 'cuda',          # GPU加速
'whisper_compute_type': 'float16', # GPU推荐
```

## 📊 成本预估

每分钟通话成本：**~$0.01-0.05**

主要成本：
- ASR (faster-whisper): 免费
- TTS (Edge TTS): 免费  
- AI (GPT-3.5): $0.002/1K tokens

示例：
- 1分钟对话 ≈ 200 tokens ≈ $0.0004
- 1000分钟/月 ≈ $11（含服务器）

## 📝 录音文件

所有通话自动录制到：
```
/home/henry/pjproject/recordings/
└── ai_call_20251107_143025.wav
```

## 🐛 故障排查

### 问题：系统无法启动

```bash
# 检查进程
ps aux | grep sip_ai_conversation

# 停止旧进程
pkill -f sip_ai_conversation.py

# 重新启动
./quick_start_ai_conversation.sh
```

### 问题：API连接错误

```bash
# 检查API Key
echo $OPENAI_API_KEY

# 重新设置
export OPENAI_API_KEY='your-key'

# 测试连接
python3 test_ai_setup.py
```

### 问题：识别不准确

```python
# 使用更大模型
'whisper_model': 'small',  # 改为 small 或 medium
```

### 问题：延迟太高

```python
# 使用更小模型
'whisper_model': 'tiny',

# 如有GPU
'whisper_device': 'cuda',
```

## 📚 详细文档

- **完整使用指南**: [AI_CONVERSATION_GUIDE.md](./AI_CONVERSATION_GUIDE.md)
- **项目总结**: [PROJECT_SUMMARY.md](./PROJECT_SUMMARY.md)
- **快速上手**: [README_AI_SYSTEM.md](./README_AI_SYSTEM.md)

## 🎯 API接口

### 发起呼叫
```bash
curl -X POST http://localhost:8089/api/call \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "82121065486"}'
```

### 挂断呼叫
```bash
curl -X POST http://localhost:8089/api/hangup
```

### 查询状态
```bash
curl -X POST http://localhost:8089/api/status
```

## 💡 小贴士

1. **首次启动会下载Whisper模型** - 需要等待几分钟
2. **测试前先准备好测试号码** - 确保对方能接听
3. **监控日志输出** - 了解AI处理过程
4. **调整VAD参数** - 根据实际通话质量优化
5. **录音可用于分析** - 改进系统效果

## 🎉 现在开始！

```bash
cd /home/henry/pjproject
./quick_start_ai_conversation.sh
```

访问：**http://localhost:8089**

祝你使用愉快！🚀🤖

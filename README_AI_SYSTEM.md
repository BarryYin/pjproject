# 🤖 AI智能对话系统 - 快速上手

## 一分钟启动

```bash
# 1. 安装依赖
./install_ai_dependencies.sh

# 2. 设置API Key
export OPENAI_API_KEY='sk-your-key-here'

# 3. 启动系统
./quick_start_ai_conversation.sh
```

## 访问控制面板

```
http://localhost:8089
```

## 系统特性

- ✅ **完全免费** ASR (faster-whisper) + TTS (Edge TTS)
- ✅ **印尼语优化** - 专为印尼语通话设计
- ✅ **低延迟** - 3-5秒响应时间
- ✅ **智能对话** - GPT-3.5驱动
- ✅ **自动录音** - 保存所有通话记录

## 工作流程

```
对方说话 → ASR识别 → AI生成回复 → TTS合成 → 播放给对方
  (实时)    (1-2秒)      (1秒)        (1-2秒)     (实时)
```

## 成本

每分钟通话: **$0.01-0.05** (仅AI API费用)

## 详细文档

查看完整文档: [AI_CONVERSATION_GUIDE.md](./AI_CONVERSATION_GUIDE.md)

## 快速测试

```bash
# API测试
curl -X POST http://localhost:8089/api/call \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "82121065486"}'
```

## 配置优化

编辑 `sip_ai_conversation.py` 中的 `CONFIG`:

```python
# 使用GPU加速
'whisper_device': 'cuda',

# 切换语音
'tts_voice': 'id-ID-GadisNeural',  # 女声

# 调整延迟
'vad_silence_duration': 1.0,  # 1秒静音后处理
```

## 故障排查

### 问题: 依赖安装失败
```bash
pip3 install faster-whisper edge-tts openai numpy --upgrade
```

### 问题: ASR识别不准
```python
# 使用更大模型
'whisper_model': 'small',  # 或 medium
```

### 问题: 延迟太高
```python
# 使用更小模型 + GPU
'whisper_model': 'tiny',
'whisper_device': 'cuda',
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `sip_ai_conversation.py` | 主程序 |
| `install_ai_dependencies.sh` | 依赖安装脚本 |
| `quick_start_ai_conversation.sh` | 快速启动脚本 |
| `AI_CONVERSATION_GUIDE.md` | 详细使用文档 |
| `recordings/` | 通话录音目录 |
| `temp_audio/` | 临时音频文件 |

## 系统架构

```
┌─────────────────────────────────────┐
│         PJSIP 音频层                 │
│    (RTP接收/发送 + 音频桥接)         │
└─────────────────────────────────────┘
              ↕
┌─────────────────────────────────────┐
│         AI处理层                     │
│  ┌─────┐  ┌─────┐  ┌─────┐         │
│  │ VAD │→│ ASR │→│ AI  │          │
│  └─────┘  └─────┘  └─────┘         │
│              ↓                       │
│          ┌─────┐                    │
│          │ TTS │                    │
│          └─────┘                    │
└─────────────────────────────────────┘
              ↕
┌─────────────────────────────────────┐
│         HTTP API层                   │
│    (Web控制面板 + REST API)         │
└─────────────────────────────────────┘
```

## 支持

- 📖 详细文档: `AI_CONVERSATION_GUIDE.md`
- 🐛 问题排查: 查看文档中的"故障排查"章节
- 💬 对话示例: 文档中有完整示例

---

**开始你的AI语音之旅！** 🚀

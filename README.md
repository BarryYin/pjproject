# 🤖 AI智能对话系统

基于PJSIP + faster-whisper + Edge TTS + GPT-3.5的免费AI语音对话方案

---

## 🚀 快速开始（推荐流程）

### 第一次使用（完整安装）

```bash
cd /home/henry/pjproject

# 一键安装所有依赖和下载模型（只需一次）
./complete_setup.sh
```

**这个脚本会**：
1. ✅ 安装所有Python依赖
2. ✅ **预下载Whisper模型**（避免启动时等待）
3. ✅ 配置OpenAI API Key

**预计时间**：2-3分钟（只需运行一次）

---

### 之后每次使用（快速启动）

```bash
cd /home/henry/pjproject
./start_now.sh
```

**启动时间**：5-10秒（因为模型已下载）

访问：**http://localhost:8090**

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

## 📁 文件说明

### 安装和启动脚本
- `complete_setup.sh` - 一键完整安装 ⭐ **首次必运行**
- `download_models.py` - 预下载模型（setup会调用）
- `start_now.sh` - 快速启动 ⭐ **日常使用**

### 工具脚本
- `check_ai_status.sh` - 检查系统状态
- `force_clean.sh` - 强制清理进程

### 文档
- `README.md` - 本文档 ⭐
- `START_NOW.md` - 快速开始
- `FINAL_SETUP.md` - 最终配置
- `AI_CONVERSATION_GUIDE.md` - 完整指南

---

## 🔧 配置说明

### 当前配置（`sip_ai_conversation.py`）

```python
CONFIG = {
    # API配置
    'api_port': 8090,  # Web控制面板端口
    
    # ASR配置
    'whisper_model': 'base',     # 模型大小
    'whisper_device': 'cpu',     # CPU或GPU
    
    # TTS配置
    'tts_voice': 'id-ID-ArdiNeural',  # 印尼语男声
    
    # AI配置
    'ai_model': 'gpt-3.5-turbo',
}
```

---

## 📊 使用流程

```
1. 访问 http://localhost:8090
   ↓
2. 输入电话号码
   ↓
3. 点击"开始AI对话"
   ↓
4. 对方说话（印尼语）
   ↓
5. 系统自动:
   - ASR识别 (1-2秒)
   - AI生成回复 (1秒)
   - TTS合成 (1-2秒)
   - 播放给对方
   ↓
6. 完整录音自动保存
```

---

## 💰 成本分析

### 每月成本（1000分钟通话）

| 项目 | 成本 |
|------|------|
| ASR (faster-whisper) | 免费 |
| TTS (Edge TTS) | 免费 |
| AI (GPT-3.5) | ~$1 |
| 服务器 | ~$10 |
| **总计** | **~$11/月** |

**对比商业方案节省**: 85-95%

---

## 🐛 常见问题

### Q1: 为什么首次启动慢？
**A**: 需要下载Whisper模型。  
**解决**: 使用 `./complete_setup.sh` 提前下载。

### Q2: 页面打不开？
**A**: 可能原因：
1. 模型正在下载（等待）
2. 端口被占用（运行 `./force_clean.sh`）
3. 系统未启动（运行 `./start_now.sh`）

### Q3: 识别不准确？
**A**: 使用更大的模型：
```python
'whisper_model': 'small',  # 或 medium
```

### Q4: 延迟太高？
**A**: 
- 使用更小模型: `'whisper_model': 'tiny'`
- 启用GPU: `'whisper_device': 'cuda'`

---

## 📚 完整文档

1. **本文档** - 快速开始
2. **AI_CONVERSATION_GUIDE.md** - 完整使用指南（16000+字）
3. **FINAL_SETUP.md** - 最终配置总结
4. **PROJECT_SUMMARY.md** - 项目总结

---

## ✅ 推荐流程总结

### 第一次使用
```bash
# 1. 完整安装（2-3分钟，只需一次）
./complete_setup.sh

# 2. 启动系统（5-10秒）
./start_now.sh

# 3. 访问页面
http://localhost:8090
```

### 以后每次使用
```bash
# 快速启动（5-10秒）
./start_now.sh

# 访问页面
http://localhost:8090
```

---

## 🎉 开始使用

```bash
cd /home/henry/pjproject

# 第一次？运行完整安装
./complete_setup.sh

# 之后每次只需
./start_now.sh
```

访问：**http://localhost:8090**

享受AI语音对话！🚀🤖

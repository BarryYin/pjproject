# 🚀 混合引擎系统启动指南

## ✅ 已完成

**系统已切换到混合引擎**：
- **ASR**: 阿里云NLS (WebSocket) - 实时语音识别
- **TTS**: 阿里云DashScope (HTTP) - 稳定语音合成

## 配置信息

### ASR（NLS）
```
AccessKey ID: <ALI_NLS_AKID> (从环境变量加载)
AppKey: <ALI_NLS_APPKEY> (从环境变量加载)
限流间隔: 3秒
限流退避: 10秒
```

### TTS（DashScope）
```
API Key: sk-ebf86b67058945fa827863a3742df0b0
Model: sambert-indah-v1 (印尼语女声)
Sample Rate: 8000Hz
限流间隔: 1秒
```

## 立即启动

### 步骤1：强制重启
```bash
./FORCE_RESTART.sh
```

### 步骤2：启动系统
```bash
./call_optimized.sh <电话号码>
```

## 验证启动

启动后**必须**看到：

```
======================================================================
  AI对话系统 - 混合引擎版
======================================================================
  ASR引擎: 阿里云NLS (WebSocket)
  TTS引擎: 阿里云DashScope (HTTP)
  回声消除: 已启用 (400ms尾长)
  智能打断: 禁用（传统模式）
======================================================================
  [ASR] 预获取Token...
  [ASR] Token: LTAI5t5fvYrtRRZ...
  [ASR] Recognizer创建成功
  [TTS] DashScope引擎初始化完成  ← 新的TTS引擎
```

### 关键检查点

- [ ] 启动信息显示 "混合引擎版"
- [ ] ASR显示 "NLS (WebSocket)"
- [ ] TTS显示 "DashScope (HTTP)"
- [ ] TTS显示 "DashScope引擎初始化完成"
- [ ] 没有 "[TTS] 预获取Token" 日志

## 运行日志

### ✅ 正常运行
```
[VAD] 句子结束 (47帧)
[ASR] 限流等待3.0s...
[ASR] 音频: 48044字节 → 'hello world' (1.1s)
[AI] 用户: 'hello world'
[AI] 回复: 'Hi there!'
[TTS] 限流等待1.0s...  ← 只等1秒！
[TTS] 文本: 'Hi there!' → 78844字节 (1.5s)
[播放] 正在播放... 预计5.0秒...
完成
```

### ✅ ASR偶尔限流
```
[ASR] ✗ 错误: TOO_MANY_REQUESTS
[ASR] ⚠ 触发限流，启动退避
[ASR] 限流退避等待10.0s...
[继续正常运行]
```

### ✅ TTS不应该限流
```
[TTS] 文本: 'Long text here' → 120844字节 (1.8s)
[TTS] 限流等待1.0s...
[TTS] 文本: 'Another text' → 89844字节 (1.6s)
[没有限流错误]  ✅
```

## 优势总结

### 之前（全NLS）
```
ASR: NLS ⚠️
TTS: NLS ⚠️
问题: 
- 共享配额
- 双重限流
- 频繁错误
```

### 现在（混合）
```
ASR: NLS ✅
TTS: DashScope ✅
优势:
- 独立配额
- TTS更快（1秒vs3秒）
- TTS不限流
- 整体更稳定
```

## 预期改善

| 指标 | 之前 | 现在 |
|-----|------|------|
| ASR限流 | 频繁 | 偶尔 |
| TTS限流 | 频繁 | 极少 |
| TTS响应 | 3秒 | 1秒 ✅ |
| 整体稳定 | 中 | 高 ✅ |

## 测试建议

### 测试1：基本功能
- 打电话
- 说话测试ASR
- 听TTS回复
- 进行多轮对话

### 测试2：压力测试
- 连续快速说话
- 观察ASR是否限流
- 观察TTS是否稳定

### 测试3：音质对比
- 听DashScope TTS音质
- 与之前NLS TTS对比
- 确认清晰度

## 如果有问题

### 问题1：TTS无声音
```bash
# 检查dashscope安装
python3 -c "import dashscope; print('OK')"

# 检查API Key
grep "sk-ebf86b67058945fa827863a3742df0b0" sip_ai_nls_optimized.py
```

### 问题2：ASR仍频繁限流
```python
# 进一步增加间隔
self.min_interval = 4.0  # 改到4秒
```

### 问题3：启动信息不对
```bash
# 确认重启了
ps aux | grep sip_ai_nls_optimized
# 应该是新进程（启动时间很近）
```

## 快速检查命令

```bash
# 1. 杀掉旧进程
pkill -9 -f sip_ai_nls_optimized

# 2. 验证配置
grep "class DashScopeTTSEngine" sip_ai_nls_optimized.py
grep "self.tts = DashScopeTTSEngine" sip_ai_nls_optimized.py

# 3. 启动
./call_optimized.sh <电话号码>
```

## 总结

✅ **系统已切换到混合引擎**
✅ **ASR用NLS（新AppKey）**
✅ **TTS用DashScope（更稳定）**
🔄 **立即重启测试**

```bash
./FORCE_RESTART.sh
./call_optimized.sh <电话号码>
```

观察：
1. TTS是否更快（1秒vs3秒）
2. TTS是否不再限流
3. ASR限流是否减少
4. 整体对话是否更流畅

如果效果好，可以考虑恢复智能打断功能！

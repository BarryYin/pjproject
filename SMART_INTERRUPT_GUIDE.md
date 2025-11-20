# 智能打断系统指南

## 问题背景

原有的打断系统过于灵敏：
- 用户说"嗯"、"哦" → 打断TTS
- 背景杂音 → 打断TTS  
- 简短回应"ya"、"oke" → 打断TTS

**期望**：只在用户说有意义的话时才打断

## 解决方案：智能打断系统

采用**三层过滤策略**：

### 第一层：VAD长度过滤
只有语音持续足够长（默认300ms）才触发打断检查

### 第二层：ASR识别
快速识别用户说了什么

### 第三层：智能判断
- **关键词过滤** - 过滤无意义词和简短回应
- **LLM语义检查**（可选）- AI判断是否真的要打断

## 架构设计

```
用户说话
  ↓
VAD检测 (持续监听)
  ↓
累积 ≥ 300ms? → NO → 继续累积
  ↓ YES
快速ASR识别
  ↓
智能判断:
  - 长度检查 (≤2字符) → 忽略
  - 关键词检查 (eh, um, ya) → 忽略
  - LLM语义检查 → YES/NO
  ↓
YES → 停止播放
NO → 继续播放
```

## 配置参数

### 基础配置
```python
CONFIG = {
    # 智能打断总开关
    'smart_interrupt_enabled': True,          # True=智能打断, False=传统打断
    
    # 最小帧数（1帧=30ms）
    'interrupt_min_frames': 10,               # 10帧 = 300ms
    
    # LLM语义检查
    'interrupt_check_semantic': True,         # True=启用LLM, False=仅关键词
    'interrupt_semantic_threshold': 0.3,      # 语义相关度阈值（暂未使用）
}
```

### 推荐配置

| 场景 | smart_interrupt | interrupt_min_frames | interrupt_check_semantic |
|------|----------------|---------------------|------------------------|
| **标准场景** ✅ | True | 10 (300ms) | True |
| 快速响应 | True | 5 (150ms) | False |
| 严格过滤 | True | 15 (450ms) | True |
| 传统模式 | False | - | - |

## 工作流程详解

### 1. VAD检测与缓冲

```python
# VAD检测到说话
if self.vad.is_speaking:
    # 累积音频帧到缓冲区
    self.interrupt_buffer.extend(self.vad.speech_frames[-5:])
    
    # 达到最小帧数 → 触发检查
    if frame_count >= CONFIG['interrupt_min_frames']:
        self.check_smart_interrupt()
```

### 2. 快速ASR识别

```python
# 取最后450ms音频进行ASR
audio_data = b''.join(self.interrupt_buffer[-15:])

# 快速识别（复用NLS连接，< 1秒）
text = self.asr.transcribe(temp_file)
# → "eh"
# → "iya"
# → "saya mau tanya sesuatu"
```

### 3. 智能判断

#### 策略1：长度检查
```python
if len(text) <= 2:
    return False, "太短(2字符)"  # 过滤 "eh", "um", "ya"
```

#### 策略2：关键词过滤
```python
filler_words = ['eh', 'em', 'um', 'uh', 'ah', 'hmm', 'hm', 'mm']
short_responses = ['ya', 'iya', 'oh', 'ok', 'oke', 'baik', 'tidak', 'nggak']

if text in filler_words:
    return False, "填充词"

if text in short_responses:
    return False, "简短回应"
```

#### 策略3：LLM语义检查（可选）

```python
prompt = """
Analyze if this user input should interrupt the current AI speech.

User said: "ya"

Reply ONLY with one word:
- "YES" if: user asks a NEW question, makes a NEW statement
- "NO" if: just acknowledgment (eh, um, ya, oke)

Answer:
"""

# GPT-3.5-turbo 快速判断
response = "NO"  # → 不打断
```

## 示例场景

### 场景1：填充词 → 不打断 ✅
```
[TTS播放中...] "Silakan rekam pesan setelah..."
[用户] "eh..."
[打断检查] 'eh' → 忽略 (填充词)
[继续播放]
```

### 场景2：简短回应 → 不打断 ✅
```
[TTS播放中...] "Apakah Anda ingin..."
[用户] "ya"
[打断检查] 'ya' → 忽略 (简短回应)
[继续播放]
```

### 场景3：新问题 → 打断 ✅
```
[TTS播放中...] "Silakan tunggu..."
[用户] "saya mau tanya sesuatu"
[打断检查] 'saya mau tanya sesuatu' → 打断! (新问题)
[停止播放]
[处理新问题]
```

### 场景4：背景噪音 → 不打断 ✅
```
[TTS播放中...] "Terima kasih..."
[背景] [咳嗽声/音乐/杂音]
[VAD检测] 时长 < 300ms → 未达到检查阈值
[继续播放]
```

## 性能优化

### 1. 快速ASR
- 复用NLS WebSocket连接
- 识别时间 < 1秒
- 不影响播放流畅度

### 2. 异步检查
```python
# 打断检查在独立线程运行
self.check_smart_interrupt()  # 非阻塞
```

### 3. 一次性检查
```python
# 避免重复检查同一段语音
if not hasattr(self, '_interrupt_checked'):
    self._interrupt_checked = True
    self.check_smart_interrupt()
```

## 调优指南

### 问题1：太灵敏，还是打断太多

**方案A：增加最小帧数**
```python
'interrupt_min_frames': 15,  # 从10改到15（450ms）
```

**方案B：启用LLM语义检查**
```python
'interrupt_check_semantic': True,
```

**方案C：添加更多关键词**
```python
self.interrupt_keywords = {
    'filler': ['eh', 'em', 'um', ...],
    'short_response': ['ya', 'iya', 'oh', 'baik', ...],
    # 添加你的语言特定词汇
}
```

### 问题2：太迟钝，应该打断时不打断

**方案A：降低最小帧数**
```python
'interrupt_min_frames': 5,  # 从10改到5（150ms）
```

**方案B：禁用LLM语义检查**
```python
'interrupt_check_semantic': False,  # 只用关键词过滤
```

**方案C：减少关键词列表**
```python
# 只保留最常见的填充词
'filler': ['eh', 'em', 'um'],
```

### 问题3：LLM调用失败

系统会自动回退到允许打断：
```python
except Exception as e:
    print(f"  [打断检查] LLM失败: {e}")
    return True, "LLM失败，允许打断"
```

## 启用/禁用

### 启用智能打断（推荐）✅
```python
CONFIG = {
    'smart_interrupt_enabled': True,
    'interrupt_min_frames': 10,
    'interrupt_check_semantic': True,
}
```

启动时显示：
```
智能打断: 已启用 (最少10帧, LLM语义:启用)
```

### 禁用智能打断（传统模式）
```python
CONFIG = {
    'smart_interrupt_enabled': False,
}
```

启动时显示：
```
智能打断: 禁用（传统打断模式）
```

## 日志输出

### 打断被触发
```
  [打断检查] 快速ASR识别中... 'saya mau tanya' → 打断! (通过基本检查)
```

### 打断被忽略
```
  [打断检查] 快速ASR识别中... 'eh' → 忽略 (填充词(eh))
  [打断检查] 快速ASR识别中... 'ya' → 忽略 (简短回应(ya))
  [打断检查] 快速ASR识别中... 'um' → 忽略 (太短(2字符))
```

### LLM语义判断
```
  [打断检查] 快速ASR识别中... 'oke' → 忽略 (LLM判断:无打断意图(oke))
  [打断检查] 快速ASR识别中... 'bagaimana caranya' → 打断! (LLM判断:有打断意图)
```

## 成本分析

### ASR成本
- 每次打断检查：1次ASR调用（450ms音频）
- 阿里云NLS：按音频时长计费

### LLM成本
- 每次打断检查（如启用）：1次GPT-3.5调用（5 tokens输出）
- 成本：< $0.001 / 次

### 建议
- **生产环境**：启用智能打断 + LLM语义检查
- **开发测试**：启用智能打断，禁用LLM（降低成本）
- **低成本**：使用传统打断模式

## 测试方法

### 测试1：填充词测试
```bash
./call_optimized.sh <电话号码>
```
TTS播放时，说：
- "eh" → 应该继续播放
- "um" → 应该继续播放
- "hmm" → 应该继续播放

### 测试2：简短回应测试
TTS播放时，说：
- "ya" → 应该继续播放
- "oke" → 应该继续播放
- "baik" → 应该继续播放

### 测试3：有意义打断测试
TTS播放时，说：
- "saya mau tanya" → 应该停止播放
- "tunggu dulu" → 应该停止播放
- "apa maksudnya" → 应该停止播放

### 测试4：背景噪音测试
TTS播放时：
- 咳嗽一声 → 应该继续播放
- 短暂杂音 → 应该继续播放

## 总结

✅ **智能打断系统优势**：
- 过滤无意义打断（eh, um, ya等）
- 降低误触发率
- 保持TTS播放完整性
- 提升用户体验

✅ **配置灵活**：
- 可调节灵敏度
- 可启用/禁用LLM
- 可自定义关键词

✅ **性能优秀**：
- 快速ASR（< 1秒）
- 异步处理
- 不影响对话流畅度

## 相关文档

- `ECHO_CANCELLATION_CONFIG.md` - 回声消除配置
- `OPTIMIZED_VERSION.md` - 系统优化说明
- `THREAD_REGISTRATION_FIX.md` - 线程安全修复

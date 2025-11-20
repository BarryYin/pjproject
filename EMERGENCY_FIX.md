# 紧急修复 - ASR错误处理

## 问题描述

系统运行时出现两个严重错误：

### 错误1：属性未定义
```
[错误] 'OptimizedNLSASREngine' object has no attribute 'max_errors'
```

### 错误2：WebSocket状态错误
```
[ASR] 异常: Must call start before send!
```

## 根本原因

### 原因1：初始化遗漏
在之前的修改中，我在 `transcribe()` 方法中使用了 `self.error_count` 和 `self.max_errors`，但忘记在 `__init__()` 方法中初始化这些属性。

### 原因2：错误处理不完整
当 `recognizer.start()` 失败后重建连接，如果重试仍然失败，代码会继续执行到 `send_audio()`，导致状态不一致。

## 修复方案

### 修复1：完整初始化
```python
class OptimizedNLSASREngine:
    def __init__(self):
        self.token = None
        self.appkey = CONFIG['nls_appkey']
        self.recognizer = None
        self.lock = threading.Lock()
        self.last_request_time = 0
        self.min_interval = 1.0  # ✅ 修复：从0.5增加到1.0
        self.error_count = 0      # ✅ 修复：添加错误计数
        self.max_errors = 3       # ✅ 修复：添加最大错误次数
```

### 修复2：改进错误处理
```python
# 启动识别
try:
    self.recognizer.start(...)
except Exception as e:
    print(f"start失败: {e}, 重建")
    self.recognizer = None
    self._create_recognizer()
    if not self.recognizer:
        self.error_count += 1
        return ""  # ✅ 提前返回，不再继续
    
    # 重试start
    try:
        self.recognizer.start(...)
    except Exception as e2:
        print(f"重试start失败: {e2}")
        self.error_count += 1
        return ""  # ✅ 再次失败，提前返回

# 发送音频（只有start成功后才执行）
try:
    for i in range(0, len(audio_data), chunk_size):
        self.recognizer.send_audio(audio_data[i:i+chunk_size])
    self.recognizer.stop()
except Exception as e:
    print(f"send/stop失败: {e}")
    self.error_count += 1
    self.recognizer = None
    self._create_recognizer()
    return ""  # ✅ 发送失败，重建连接
```

## 修复前后对比

### 修复前 ❌
```python
# __init__中缺少属性
self.min_interval = 0.5  # 太短，容易限流

# 错误处理不完整
except Exception as e:
    self.recognizer = None
    self._create_recognizer()
    self.recognizer.start(...)  # 可能失败但继续执行
    
# 继续发送（状态可能不对）
self.recognizer.send_audio(...)  # ❌ 如果start失败会报错
```

### 修复后 ✅
```python
# __init__完整初始化
self.min_interval = 1.0
self.error_count = 0
self.max_errors = 3

# 完整的错误处理
except Exception as e:
    self.recognizer = None
    self._create_recognizer()
    if not self.recognizer:
        return ""  # ✅ 提前返回
    
    try:
        self.recognizer.start(...)
    except:
        return ""  # ✅ 失败返回

# 只有start成功才发送
try:
    self.recognizer.send_audio(...)
except Exception as e:
    self.recognizer = None
    return ""  # ✅ 安全处理
```

## 测试验证

### 正常场景
```
[ASR] 音频: 48044字节 → 'hello world' (1.1s)
```

### start失败场景
```
[ASR] 音频: 48044字节 start失败: xxx, 重建
[ASR] Recognizer创建成功
→ '' (0.1s)
```

### 重试失败场景
```
[ASR] 音频: 48044字节 start失败: xxx, 重建
[ASR] Recognizer创建成功
重试start失败: xxx
→ '' (0.1s)
```

### send失败场景
```
[ASR] 音频: 48044字节 [ASR] ✓ 已启动
send/stop失败: xxx
[ASR] Recognizer创建成功
→ '' (0.5s)
```

## 相关修复

同样的逻辑也应用到了 `OptimizedNLSTTSEngine`：
- ✅ 添加 `error_count` 和 `max_errors`
- ✅ 增加 `min_interval` 到 1.0秒
- ✅ 改进错误处理和连接重建

## 预期效果

1. **不再有属性错误** - 所有属性都正确初始化
2. **更好的错误恢复** - 失败时安全返回，不会导致状态不一致
3. **减少限流错误** - 1秒间隔减少请求频率
4. **自动重建连接** - 连续3次错误自动重建

## 启动测试

```bash
./call_optimized.sh <电话号码>
```

### 期望看到
```
======================================================================
  AI对话系统 - NLS优化版（长连接）
======================================================================
  特性: WebSocket长连接复用，极速ASR/TTS
  回声消除: 已启用 (400ms尾长)
  智能打断: 已启用 (最少15帧, LLM语义:禁用)
======================================================================
[SIP] 账户: 6281479242434
[拨号] sip:13462xxxxx@147.139.205.88
```

### 不应该看到
```
❌ 'OptimizedNLSASREngine' object has no attribute 'max_errors'
❌ Must call start before send!
```

## 文件修改

- `sip_ai_nls_optimized.py`
  - Line 144-152: ASR `__init__` 方法
  - Line 244-286: ASR `transcribe` 错误处理
  - Line 315-320: TTS `__init__` 方法  
  - Line 443-461: TTS `synthesize` 错误处理

## 相关文档

- `RATE_LIMIT_AND_TIMEOUT_FIX.md` - 限流和超时修复详解
- `SMART_INTERRUPT_GUIDE.md` - 智能打断系统
- `CALL_DISCONNECT_FIX_SUMMARY.md` - 通话断开修复

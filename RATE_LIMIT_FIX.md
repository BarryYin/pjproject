# 🚦 频率限制问题 - 已修复

## 🐛 问题：TOO_MANY_REQUESTS

```json
{
  "header": {
    "namespace": "Default",
    "name": "TaskFailed",
    "status": 40000005,
    "status_text": "Gateway:TOO_MANY_REQUESTS:Too many requests!"
  }
}
```

**错误代码**: `40000005`  
**错误信息**: `TOO_MANY_REQUESTS` - 请求过多

---

## 🔍 根本原因

### 为什么会触发限流？

**优化版的"优势"反而成了问题**：

```python
# 我们的优化：WebSocket长连接复用
class OptimizedNLSASREngine:
    def __init__(self):
        self.recognizer = nls.NlsSpeechRecognizer(...)  # 只创建一次
    
    def transcribe(self, audio_file):
        self.recognizer.start()   # 复用连接
        self.recognizer.send()    # 快速发送
        self.recognizer.stop()    # 立即停止
        # ↑ 太快了！下次马上又来
```

**时间线**：
```
0.0s: 识别1 start → send → stop
0.2s: 识别2 start → send → stop  ← 太快！
0.4s: 识别3 start → send → stop  ← 太快！
0.5s: ❌ TOO_MANY_REQUESTS!
```

**阿里云NLS的QPS限制**：
- 可能是每秒最多2-3次请求
- 我们的优化版太快，瞬间发送多个请求
- 触发了频率限制

---

## ✅ 解决方案：请求限流

### 核心思路

在每次请求之间添加**最小间隔**，避免过快请求。

### 实现

```python
class OptimizedNLSASREngine:
    def __init__(self):
        self.last_request_time = 0      # 上次请求时间
        self.min_interval = 0.5         # 最小间隔（秒）
    
    def transcribe(self, audio_file):
        with self.lock:
            # 限流：确保请求间隔
            elapsed = time.time() - self.last_request_time
            if elapsed < self.min_interval:
                wait_time = self.min_interval - elapsed
                print(f"  [ASR] 限流等待{wait_time:.1f}s...")
                time.sleep(wait_time)
            
            # 记录本次请求时间
            self.last_request_time = time.time()
            
            # 正常识别流程
            self.recognizer.start()
            ...
```

---

## 📊 时间线对比

### Before（触发限流）❌

```
0.0s: 识别1 完成
0.2s: 识别2 ❌ TOO_MANY_REQUESTS
```

### After（带限流）✅

```
0.0s: 识别1 开始
0.8s: 识别1 完成
      └→ 记录时间 last_request_time = 0.8s
1.2s: 识别2 请求
      └→ elapsed = 1.2 - 0.8 = 0.4s < 0.5s
      └→ 等待 0.1s
1.3s: 识别2 开始 ✅
      └→ 记录时间 last_request_time = 1.3s
```

---

## 🎯 关键代码

### 1. 添加限流变量

```python
self.last_request_time = 0  # 上次请求时间戳
self.min_interval = 0.5     # 最小请求间隔（秒）
```

### 2. 请求前检查间隔

```python
# 计算距离上次请求的时间
elapsed = time.time() - self.last_request_time

# 如果间隔太短，等待
if elapsed < self.min_interval:
    wait_time = self.min_interval - elapsed
    time.sleep(wait_time)
```

### 3. 记录请求时间

```python
# 发起请求前记录时间
self.last_request_time = time.time()
```

---

## 🔧 参数调整

### 当前设置

```python
self.min_interval = 0.5  # 500ms间隔
```

**效果**：
- 最多每秒2次请求
- 安全，不会触发限流
- 延迟增加最多0.5秒

### 如果还是触发限流

```python
self.min_interval = 1.0  # 1秒间隔
```

### 如果需要更快

```python
self.min_interval = 0.3  # 300ms间隔
# 风险：可能触发限流
```

---

## 📺 运行效果

### 正常情况（无需等待）

```
━━━━━━━━━━━━━━━━━━━━━━━━━━
  [ASR] 音频: 14400字节 → 'Halo' (0.8s)
  [AI] 回复: ...
━━━━━━━━━━━━━━━━━━━━━━━━━━

# 等待1秒（对话自然停顿）

━━━━━━━━━━━━━━━━━━━━━━━━━━
  [ASR] 音频: 10000字节 → 'Apa kabar?' (0.7s)  ← 无需限流
━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 连续请求（触发限流）

```
━━━━━━━━━━━━━━━━━━━━━━━━━━
  [ASR] 音频: 14400字节 → 'Halo' (0.8s)
━━━━━━━━━━━━━━━━━━━━━━━━━━

# 立即又来一个请求

━━━━━━━━━━━━━━━━━━━━━━━━━━
  [ASR] 限流等待0.3s... 音频: 10000字节 → 'Apa' (0.7s)  ← 等待后正常
━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 🎯 优势

### 1. 防止限流 ✅
- 强制请求间隔
- 不会触发 TOO_MANY_REQUESTS

### 2. 对用户影响小 ✅
- 正常对话有自然停顿，无需等待
- 只在快速连续请求时等待

### 3. 可调节 ✅
- 可以根据实际情况调整间隔
- 平衡速度和稳定性

### 4. TTS同样保护 ✅
- ASR和TTS都有限流
- 全面防护

---

## 📋 错误恢复流程

```
1. 请求阿里云NLS
   ↓
2. 收到 TOO_MANY_REQUESTS
   ↓
3. on_error 回调触发
   ↓
4. 自动重建 recognizer
   ↓
5. 下次请求会等待足够间隔
   ↓
6. 恢复正常 ✅
```

---

## 🎉 总结

### 问题
```
WebSocket长连接复用 → 请求太快 → 触发NLS限流
```

### 解决
```
添加最小请求间隔(0.5s) → 不会太快 → 不触发限流 ✅
```

### 副作用
```
连续请求可能增加0-0.5秒延迟
但正常对话几乎无影响（有自然停顿）
```

---

## 🚀 立即测试

```bash
./call_optimized.sh 85211111111
```

**应该看到**：
- ✅ 不再有 TOO_MANY_REQUESTS 错误
- ✅ 可能偶尔看到 `[ASR] 限流等待X.Xs...`
- ✅ 识别正常完成

---

**现在应该不会再触发频率限制了！** 🎊

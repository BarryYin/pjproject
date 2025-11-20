# NLS WebSocket限流的真相

## 关键问题

> "为什么ASR和TTS连上WebSocket后，还会限流？持续连接不应该避免限流吗？"

## 核心答案

**WebSocket长连接 ≠ 无限流**

WebSocket连接持续，但**每次调用 `.start()` 算一次请求**！

## 工作原理详解

### NLS WebSocket的请求模型

```python
# 1. 建立WebSocket连接（一次）
recognizer = nls.NlsSpeechRecognizer(
    token=token,
    appkey=appkey,
    ...
)
# ✅ WebSocket连接建立

# 2. 使用连接进行多次识别
recognizer.start()         # ← 请求1：开始识别
recognizer.send_audio(...)  # ← 发送音频数据
recognizer.stop()          # ← 结束识别

recognizer.start()         # ← 请求2：开始识别
recognizer.send_audio(...)  # ← 发送音频数据
recognizer.stop()          # ← 结束识别

recognizer.start()         # ← 请求3：开始识别
...
```

### 关键点

1. **WebSocket连接**: 持续打开（不关闭）
2. **每次 `start()`**: 算一次新的识别请求
3. **限流计数**: 基于 `start()` 调用次数，不是连接数

## 为什么会限流？

### 阿里云NLS的限流规则

```
免费版配额示例：
- 每秒最多: 2次 start() 调用
- 每分钟最多: 60次 start() 调用
- 每天最多: 10000次 start() 调用
```

### 你的场景

```
用户每隔几秒说话：
t=0s:  start() → 识别 "hello"
t=2s:  start() → 识别 "world"
t=3s:  start() → 识别 "hi"      ← TOO_MANY_REQUESTS！
t=4s:  start() → 识别 "bye"     ← TOO_MANY_REQUESTS！
```

**原因**: 3秒内调用了3次 `start()`，超过"每秒2次"的限制。

## 对比：连接 vs 请求

### 连接（Connection）

```
建立WebSocket: 一次（程序启动时）
  ↓
[WebSocket保持连接]
  ↓
关闭连接: 一次（程序退出时）
```

**优势**:
- 不用反复握手
- 响应更快
- 节省资源

### 请求（Request）

```
start() 第1次 → 识别请求1
start() 第2次 → 识别请求2
start() 第3次 → 识别请求3 ← 可能触发限流！
...
```

**限流基于请求数**，不是连接数！

## 类比理解

### HTTP vs WebSocket

**HTTP模式（短连接）**:
```
请求1: [连接 → 识别 → 关闭]  (耗时0.5s)
请求2: [连接 → 识别 → 关闭]  (耗时0.5s)
请求3: [连接 → 识别 → 关闭]  (耗时0.5s)
```

**WebSocket模式（长连接）**:
```
启动: [建立连接]  (耗时0.5s)
请求1: [识别]  (耗时0.1s) ← 快！
请求2: [识别]  (耗时0.1s) ← 快！
请求3: [识别]  (耗时0.1s) ← 快！
结束: [关闭连接]
```

**但限流规则是一样的**:
- HTTP: 每秒最多2次 API 调用
- WebSocket: 每秒最多2次 `start()` 调用

## NLS SDK的实现

### 每次 `start()` 做了什么

```python
recognizer.start(
    aformat="pcm",
    sample_rate=8000,
    enable_intermediate_result=False
)
```

SDK内部：
```
1. 生成task_id (唯一识别ID)
2. 通过WebSocket发送 StartTranscription 消息到服务器
3. 服务器收到，计数+1 (限流检查)
4. 如果超过配额 → 返回 TOO_MANY_REQUESTS
5. 如果未超过 → 开始接收音频
```

### 服务器端的限流计数

```
阿里云服务器：
- 记录你的 AppKey
- 统计每秒/每分钟的 start() 次数
- 超过配额 → 返回 TOO_MANY_REQUESTS
- WebSocket连接保持打开（不关闭）
```

## 为什么不能避免限流？

### 误解

❌ **错误想法**: "WebSocket长连接 = 可以无限制调用"

### 真相

✅ **实际情况**:
- WebSocket只是**通信方式**
- 限流基于**业务请求次数**
- `start()` = 一次业务请求
- 请求太频繁 → 限流

### 类比

**电话 vs 打电话次数**

```
持续通话（长连接）:
- 电话线一直接通 ✅
- 但你说话太快，对方听不清 → "请慢点说"（限流）

不是电话线的问题，是说话频率的问题！
```

## 如何避免限流？

### 方案1：增加请求间隔（当前方案）

```python
self.min_interval = 3.0  # 每次start()至少间隔3秒

def transcribe(self, audio_file):
    # 等待足够时间
    elapsed = time.time() - self.last_request_time
    if elapsed < self.min_interval:
        wait_time = self.min_interval - elapsed
        time.sleep(wait_time)
    
    # 现在才调用start()
    self.recognizer.start(...)
```

**效果**: 确保每秒最多0.33次 `start()`，远低于配额

### 方案2：升级配额（推荐）

联系阿里云升级配额：
```
免费版: 2次/秒 → 商业版: 10次/秒
```

这样可以：
- 减少间隔到0.5秒
- 恢复智能打断
- 更快响应

### 方案3：批量处理（不适用）

```python
# 不适用于实时语音对话
# 只适用于离线批处理
```

### 方案4：多账号轮询（不推荐）

```python
# 使用多个AppKey轮流调用
# 复杂且违反服务条款
```

## 当前配置分析

### ASR（NLS）配置

```python
min_interval = 3.0  # 每次请求间隔3秒
rate_limit_backoff = 10.0  # 触发限流后退避10秒
max_errors = 3  # 连续3次错误才重建连接
```

**计算**:
- 每次 `start()` 间隔3秒
- 每秒最多: 0.33次请求
- 远低于配额限制（2次/秒）

**为什么还限流？**

可能原因：
1. 新AppKey配额更低（<2次/秒）
2. 账号欠费或被限制
3. 其他地方也在用这个AppKey

### TTS（DashScope）配置

```python
min_interval = 1.0  # 每次请求间隔1秒
```

**计算**:
- 每次 `call()` 间隔1秒
- 每秒最多: 1次请求
- DashScope限流更宽松

## 测试验证

### 测试1：观察start()频率

启动程序，观察日志：
```bash
./call_optimized.sh <电话号码>
```

观察：
```
[ASR] 音频: 48044字节 → 'hello' (1.1s)
[ASR] 限流等待3.0s...  ← 检查是否真的等待了3秒
[ASR] 音频: 30284字节 → 'world' (1.0s)
[ASR] 限流等待3.0s...
```

计算两次 "音频:" 之间的实际时间差：
```
应该 ≥ 3秒
```

### 测试2：检查AppKey配额

```bash
# 咨询阿里云客服
# 查询 AppKey: gtYJLzS47I0Dx1TO 的配额
```

可能的回复：
```
- 每秒最多: 1次 (太低！)
- 每秒最多: 2次 (正常)
- 每秒最多: 10次 (商业版)
```

### 测试3：临时禁用限流保护

```python
# 临时测试（不推荐用于生产）
self.min_interval = 0.0  # 禁用间隔

# 快速连续调用，看多久触发限流
```

这可以确定真实配额。

## 解决方案总结

### 短期方案（当前）

✅ **已实施**:
- ASR间隔3秒
- TTS间隔1秒
- 触发限流后退避10秒
- 禁用智能打断（减少请求）

### 中期方案

🔄 **建议**:
1. 联系阿里云确认配额
2. 如果配额<2次/秒，升级到商业版
3. 或进一步增加间隔到5秒

### 长期方案

🎯 **理想**:
1. 升级到商业版配额（10次/秒）
2. 减少间隔到0.5秒
3. 恢复智能打断
4. 更好的用户体验

## 回答你的问题

### Q1: 为什么会限流？

**A**: 因为 `start()` 调用太频繁，超过AppKey配额。WebSocket连接持续，但**请求次数有限制**。

### Q2: 连上后可以持续吗？

**A**: 
- WebSocket连接: ✅ 可以持续（一直打开）
- start()调用: ❌ 有频率限制（配额）

### Q3: 怎么能不触发限流？

**A**: 
1. ✅ 增加间隔（当前3秒）
2. ✅ 升级配额（联系阿里云）
3. ✅ 减少请求（禁用打断）
4. ✅ 退避策略（触发后等待）

## 类比总结

**WebSocket长连接**就像**包月电话卡**：

```
包月卡（WebSocket）:
- 电话线一直接通 ✅ (连接持续)
- 但每月只能打100分钟 ❌ (配额限制)
- 超过100分钟 → 限流 (TOO_MANY_REQUESTS)

解决方案:
1. 少打电话（增加间隔）
2. 升级套餐（升级配额）
3. 打短一点（减少请求）
```

## 最终建议

1. **立即执行**:
   ```bash
   ./FORCE_RESTART.sh
   ./call_optimized.sh <电话号码>
   ```

2. **观察日志**:
   - 是否还有 `TOO_MANY_REQUESTS`？
   - 间隔是否真的是3秒？

3. **联系阿里云**:
   - 查询AppKey配额
   - 考虑升级到商业版

4. **调整策略**:
   - 如果还限流 → 增加到5秒
   - 如果不限流 → 可以减少到2秒

**核心理解**: WebSocket只是通信方式，限流基于业务请求次数！

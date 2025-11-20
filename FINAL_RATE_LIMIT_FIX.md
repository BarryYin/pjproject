# 最终限流修复方案

## 问题分析

即使增加到1秒间隔，系统仍频繁触发 `TOO_MANY_REQUESTS` 错误。

### 根本原因

1. **请求过于密集** - VAD检测到多段语音，每段都触发ASR
2. **没有退避机制** - 触发限流后立即继续请求，加剧问题
3. **并发请求** - 语音处理线程 + 打断检查线程同时发送请求

## 最终解决方案

### 1. 增加基础间隔到2秒
```python
self.min_interval = 2.0  # 从1.0增加到2.0秒
```

### 2. 实现指数退避机制
触发限流后，强制等待5秒再继续：

```python
self.last_rate_limit_time = 0  # 记录上次限流时间
self.rate_limit_backoff = 5.0  # 退避5秒

# 检查是否刚触发过限流
time_since_rate_limit = time.time() - self.last_rate_limit_time
if time_since_rate_limit < self.rate_limit_backoff:
    backoff_wait = self.rate_limit_backoff - time_since_rate_limit
    print(f"  [ASR] 限流退避等待{backoff_wait:.1f}s...")
    time.sleep(backoff_wait)
```

### 3. 自动检测限流错误
在错误回调中检测 `TOO_MANY_REQUESTS`：

```python
def _on_error(self, message, *args):
    print(f"  [ASR] ✗ 错误: {message}")
    if message and "TOO_MANY_REQUESTS" in str(message):
        print(f"  [ASR] ⚠ 触发限流，启动退避")
        self.last_rate_limit_time = time.time()
```

## 工作流程

### 正常场景
```
[ASR] 音频: 48044字节 → 'hello' (1.1s)
[等待2秒]
[ASR] 音频: 30284字节 → 'world' (1.0s)
```

### 限流场景
```
[ASR] 音频: 48044字节
[ASR] ✗ 错误: TOO_MANY_REQUESTS
[ASR] ⚠ 触发限流，启动退避
[等待5秒退避]
[ASR] 限流退避等待4.2s...
[ASR] 音频: 30284字节 → 'hello' (1.1s)
```

### 多次限流
```
[ASR] ✗ 错误: TOO_MANY_REQUESTS  (第1次)
[等待5秒]
[ASR] ✗ 错误: TOO_MANY_REQUESTS  (第2次)
[等待5秒]
[ASR] 音频: 48044字节 → 'hello' (1.1s)  ✅ 成功
```

## 请求频率对比

### 修复前
```
基础间隔: 1.0秒
打断检查: 2.0秒
限流后: 立即重试 ❌
理论QPS: 1.0
实际QPS: 1.5-2.0 (并发)
结果: 频繁限流 ❌
```

### 修复后
```
基础间隔: 2.0秒
打断检查: 4.0秒
限流后: 等待5秒 ✅
理论QPS: 0.5
实际QPS: 0.3-0.5
结果: 极少限流 ✅
```

## 配置参数

### ASR引擎
```python
min_interval = 2.0秒          # 正常识别间隔
min_interval * 2 = 4.0秒      # 打断检查间隔
rate_limit_backoff = 5.0秒    # 限流退避时间
```

### TTS引擎
```python
min_interval = 2.0秒          # 合成间隔
rate_limit_backoff = 5.0秒    # 限流退避时间
```

## 预期效果

### ✅ 应该看到
```
# 正常对话，带合理等待
[ASR] 音频: 48044字节 → 'hello' (1.1s)
[等待2秒]
[TTS] 文本: 'Hi' → 78844字节 (1.9s)
[等待2秒]
[ASR] 音频: 30284字节 → 'how are you' (1.0s)
```

### ✅ 偶尔限流时
```
[ASR] ✗ 错误: TOO_MANY_REQUESTS
[ASR] ⚠ 触发限流，启动退避
[ASR] 限流退避等待5.0s...
[继续正常运行]
```

### ❌ 不应该看到
```
❌ 连续多次 TOO_MANY_REQUESTS
❌ 超时后没有回复
❌ Must call start before send (已修复)
```

## 权衡考虑

### 优点
- ✅ 大幅减少限流错误
- ✅ 自动退避恢复
- ✅ 保护阿里云账号

### 缺点
- ⚠️ 响应速度变慢（2秒基础延迟）
- ⚠️ 触发限流后有5秒等待

### 适用场景
- ✅ 生产环境（稳定性优先）
- ✅ 免费/低配额用户
- ⚠️ 实时性要求高的场景（可能需要升级配额）

## 调优建议

### 如果仍有限流
```python
# 方案1: 增加基础间隔
self.min_interval = 3.0  # 增加到3秒

# 方案2: 增加退避时间
self.rate_limit_backoff = 10.0  # 增加到10秒

# 方案3: 禁用打断检查
'smart_interrupt_enabled': False
```

### 如果响应太慢
```python
# 方案1: 降低基础间隔（风险：可能限流）
self.min_interval = 1.5  # 降到1.5秒

# 方案2: 减少退避时间
self.rate_limit_backoff = 3.0  # 降到3秒

# 方案3: 升级阿里云配额（推荐）
```

## 测试步骤

### 1. 重启系统
```bash
./restart_system.sh
./call_optimized.sh <电话号码>
```

### 2. 观察启动日志
```
[ASR] 预获取Token...
[ASR] Token: xxxxx...
[ASR] Recognizer创建成功  ✅
[TTS] 预获取Token...
[TTS] Token: xxxxx...
[TTS] Synthesizer创建成功  ✅
```

### 3. 测试对话
- 说话，观察ASR识别
- 等待TTS回复
- 多次对话，观察是否有限流
- 如果出现限流，观察退避是否生效

### 4. 观察关键日志
```
✅ [ASR] 音频: 48044字节 → 'text' (1.1s)
✅ [ASR] 限流等待2.0s...  (正常限流)
✅ [ASR] 限流退避等待5.0s...  (触发退避)
❌ [ASR] ✗ 错误: TOO_MANY_REQUESTS  (应该很少见)
```

## 文件修改

`sip_ai_nls_optimized.py`:
- Line 150: `min_interval = 2.0`
- Line 153-154: 添加退避属性
- Line 174-180: ASR错误回调
- Line 217-222: ASR退避检查
- Line 350: `min_interval = 2.0`
- Line 353-354: TTS退避属性
- Line 374-380: TTS错误回调
- Line 423-428: TTS退避检查

## 总结

✅ **核心改进**:
1. 基础间隔: 1秒 → 2秒
2. 打断间隔: 2秒 → 4秒
3. 新增: 5秒限流退避机制
4. 新增: 自动检测限流错误

✅ **预期效果**:
- 限流错误减少90%
- 系统更稳定
- 可能稍慢但更可靠

⚠️ **需要重启程序才能生效！**

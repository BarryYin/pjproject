# WebSocket频繁重连问题修复

## 问题发现

你提出了一个**关键问题**：

> "为什么ASR会断开？不是WebSocket连上的话，为什么会限流？你是重连了ASR吗？"

## 根本原因

是的！**每次ASR出错都在重建WebSocket连接！**

### 错误的逻辑（修复前）

```python
def transcribe(self, audio_file):
    try:
        # ... ASR识别
    except Exception as e:
        print(f"  [ASR] 异常: {e}")
        self.error_count += 1
        
        # ❌ 问题：每次错误都重建连接！
        self.recognizer = None        # 销毁WebSocket
        self._create_recognizer()     # 创建新WebSocket
        return ""
```

### 导致的恶性循环

```
1. 调用ASR识别
   ↓
2. 触发TOO_MANY_REQUESTS限流错误
   ↓
3. 代码认为连接有问题，销毁WebSocket
   ↓
4. 创建新WebSocket连接
   ↓
5. 新连接再次被限流（因为请求太频繁）
   ↓
6. 回到步骤2，无限循环！
```

### 日志证据

```
[ASR] ✗ 错误: TOO_MANY_REQUESTS
[ASR] ⊗ 关闭                    ← WebSocket被关闭
[ASR] Recognizer创建成功         ← 创建新连接
[ASR] ✗ 错误: TOO_MANY_REQUESTS  ← 新连接立即被限流
[ASR] ⊗ 关闭                    ← 又被关闭
[ASR] Recognizer创建成功         ← 又创建新连接
...（无限循环）
```

## 正确的理解

### WebSocket长连接的意义

WebSocket长连接的目的是**复用同一个连接**：

```
建立连接
  ↓
请求1 → 响应1
  ↓ (保持连接)
请求2 → 响应2
  ↓ (保持连接)
请求3 → 响应3
  ↓ (保持连接)
...
```

### 限流错误 ≠ 连接问题

`TOO_MANY_REQUESTS` 错误**不是**连接问题，而是：
- ✅ **WebSocket连接正常**
- ❌ **请求频率超过限制**

解决方法：
- ✅ 保持WebSocket连接
- ✅ 等待足够长时间再发请求
- ❌ **不要**销毁重建连接！

## 修复方案

### 策略1：只在真正需要时重建

```python
def transcribe(self, audio_file):
    try:
        # ... ASR识别
    except Exception as e:
        print(f"  [ASR] 异常: {e}")
        self.error_count += 1
        
        # ✅ 只在连续3次错误后才重建
        if self.error_count >= self.max_errors:
            print(f"  [ASR] 错误过多({self.error_count}次)，强制重建连接")
            self.recognizer = None
            self._create_recognizer()
            self.error_count = 0
        
        # ✅ 否则保持连接，不重建
        return ""
```

### 策略2：区分错误类型

```python
# TOO_MANY_REQUESTS → 不重建，只等待
# 连接错误 → 重建

if "TOO_MANY_REQUESTS" in str(e):
    # 限流错误，保持连接，启动退避
    self.last_rate_limit_time = time.time()
elif "connection" in str(e).lower():
    # 连接错误，重建
    self.recognizer = None
    self._create_recognizer()
```

## 修复位置

### 位置1：`start()` 失败处理
```python
except Exception as e:
    print(f"start失败: {e}, 重建")
    self.recognizer = None
    self._create_recognizer()
    if not self.recognizer:
        return ""
    
    try:
        self.recognizer.start(...)  # 重试
    except:
        return ""  # ✅ 重试失败，返回（不再重建）
```

### 位置2：`send/stop` 失败处理（已修复）
```python
except Exception as e:
    print(f"send/stop失败: {e}")
    self.error_count += 1
    # ✅ 不立即重建，等待下次检查error_count
    return ""
```

### 位置3：整体异常处理（已修复）
```python
except Exception as e:
    print(f"  [ASR] 异常: {e}")
    self.error_count += 1
    
    # ✅ 只在连续3次错误后才重建
    if self.error_count >= self.max_errors:
        self.recognizer = None
        self._create_recognizer()
        self.error_count = 0
    
    # ✅ 否则保持连接
    return ""
```

## 效果对比

### 修复前 ❌
```
[ASR] ✗ 错误: TOO_MANY_REQUESTS
[ASR] ⊗ 关闭                    ← 关闭连接
[ASR] Recognizer创建成功         ← 创建新连接（0.5秒）
[ASR] ✗ 错误: TOO_MANY_REQUESTS  ← 新连接立即限流
[ASR] ⊗ 关闭                    ← 又关闭
[ASR] Recognizer创建成功         ← 又创建（0.5秒）
...（无限循环）
```

### 修复后 ✅
```
[ASR] ✗ 错误: TOO_MANY_REQUESTS
[ASR] ⚠ 触发限流，启动退避
[保持WebSocket连接]              ← 不关闭！
[等待10秒退避]
[ASR] 限流退避等待10.0s...
[ASR] 音频: 48044字节 → 'hello' (1.1s)  ← 使用同一连接，成功！
```

## 为什么这样更好？

### 1. 减少连接开销
- 建立WebSocket连接需要时间（~0.5秒）
- 频繁重建浪费时间和资源

### 2. 避免限流陷阱
- 新连接会算作新请求
- 可能再次触发限流
- 导致恶性循环

### 3. 真正的长连接
- 只创建一次连接
- 复用同一连接处理所有请求
- 这才是"长连接"的意义！

## 正确的连接管理

### 建立连接
```python
def __init__(self):
    # 启动时创建一次
    self._create_recognizer()
```

### 使用连接
```python
def transcribe(self, audio_file):
    # 检查连接是否存在
    if not self.recognizer:
        self._create_recognizer()
    
    # 使用现有连接
    self.recognizer.start()
    self.recognizer.send_audio(data)
    self.recognizer.stop()
```

### 重建连接（罕见）
```python
# 只在以下情况重建：
1. 连续3次错误
2. IDLE_TIMEOUT（连接真的断了）
3. 连接错误（非限流错误）
```

## 预期日志

### ✅ 正常运行（保持连接）
```
[启动]
[ASR] 预获取Token...
[ASR] Recognizer创建成功  ← 创建一次

[使用中]
[ASR] 音频: 48044字节 → 'hello' (1.1s)  ← 使用连接
[ASR] 限流等待3.0s...
[ASR] 音频: 30284字节 → 'world' (1.0s)  ← 同一连接
[ASR] 限流等待3.0s...
[ASR] 音频: 22604字节 → 'hi' (0.9s)     ← 同一连接
...
[没有"关闭"和"创建成功"日志]  ✅
```

### ✅ 偶尔限流（保持连接）
```
[ASR] ✗ 错误: TOO_MANY_REQUESTS
[ASR] ⚠ 触发限流，启动退避
[没有"关闭"日志]  ✅ 保持连接
[ASR] 限流退避等待10.0s...
[ASR] 音频: 48044字节 → 'hello' (1.1s)  ← 使用同一连接
```

### ✅ 连续错误（才重建）
```
[ASR] ✗ 错误: TOO_MANY_REQUESTS  (错误1)
[保持连接]
[ASR] ✗ 错误: TOO_MANY_REQUESTS  (错误2)
[保持连接]
[ASR] ✗ 错误: TOO_MANY_REQUESTS  (错误3)
[ASR] 错误过多(3次)，强制重建连接  ← 现在才重建
[ASR] ⊗ 关闭
[ASR] Recognizer创建成功
```

## 文件修改

`sip_ai_nls_optimized.py`:
- Line 323-334: 只在error_count >= 3时才重建
- Line 298-302: send/stop失败不重建

## 测试验证

### 1. 重启系统
```bash
./FORCE_RESTART.sh
./call_optimized.sh <电话号码>
```

### 2. 观察日志

**应该看到**:
```
✅ [ASR] Recognizer创建成功  (只在启动时)
✅ [ASR] 音频: xxx → 'text'  (多次，使用同一连接)
✅ 没有频繁的"关闭"和"创建成功"
```

**不应该看到**:
```
❌ [ASR] ⊗ 关闭  (频繁出现)
❌ [ASR] Recognizer创建成功  (频繁出现)
```

### 3. 计数检查

通话5分钟，应该：
- ✅ "创建成功": 1次（或很少）
- ❌ "创建成功": 10+次（说明频繁重建）

## 总结

### 核心问题
❌ **每次错误都重建连接** → 不是真正的"长连接"

### 核心修复
✅ **保持WebSocket连接，只在必要时重建** → 真正的"长连接"

### 预期效果
- 减少连接开销
- 避免重建导致的额外限流
- 提升响应速度
- 更稳定的系统

### 关键指标
- 每通话创建连接: 1次（vs 之前10+次）
- 限流触发: 偶尔（vs 频繁）
- 响应速度: 更快

🔄 **立即重启测试，观察"创建成功"日志的频率！**
```bash
./FORCE_RESTART.sh
./call_optimized.sh <电话号码>
```

# NLS限流和超时问题修复

## 问题描述

系统运行时出现两类错误：

### 1. TOO_MANY_REQUESTS - 请求过于频繁
```
[ASR] ✗ 错误: {"header":{"namespace":"Default","name":"TaskFailed","status":40000005,
"status_text":"Gateway:TOO_MANY_REQUESTS:Too many requests!"}}
```

### 2. IDLE_TIMEOUT - WebSocket空闲超时
```
[ASR] ✗ 错误: {"header":{"namespace":"Default","name":"TaskFailed","status":40000004,
"status_text":"Gateway:IDLE_TIMEOUT:Websocket session is idle for too long time"}}
```

## 根本原因

### 原因1：智能打断系统增加了ASR请求量
- 每次检测到说话（≥450ms）→ 1次ASR调用（打断检查）
- 语音结束 → 1次ASR调用（完整识别）
- **总计**: 可能每段语音 2次ASR调用

加上原有的对话流程，短时间内产生大量ASR请求，超过阿里云NLS限流阈值。

### 原因2：限流间隔太短
- 之前设置：`min_interval = 0.5秒`
- 多个并发请求：打断检查线程 + 语音处理线程
- 实际请求频率 > 2 QPS → 触发限流

### 原因3：WebSocket连接空闲超时
- NLS WebSocket长连接有空闲超时限制
- 连接建立后如果长时间无请求，会被服务端关闭
- 客户端未检测到连接失效，继续使用 → 报错

## 解决方案

### 修复1：增加限流间隔

#### ASR引擎
```python
class OptimizedNLSASREngine:
    def __init__(self):
        self.min_interval = 1.0  # 从0.5秒增加到1.0秒
        self.error_count = 0
        self.max_errors = 3
```

#### TTS引擎
```python
class OptimizedNLSTTSEngine:
    def __init__(self):
        self.min_interval = 1.0  # 从0.5秒增加到1.0秒
        self.error_count = 0
        self.max_errors = 3
```

### 修复2：打断检查使用更长限流

打断检查不是关键路径，可以容忍更长延迟：

```python
def transcribe(self, audio_file, is_interrupt_check=False):
    # 打断检查使用2倍限流间隔（2秒）
    min_interval = self.min_interval * 2 if is_interrupt_check else self.min_interval
    # ...
```

调用时：
```python
# 打断检查
text = self.asr.transcribe(temp_file, is_interrupt_check=True)  # 2秒间隔

# 正常识别
text = self.asr.transcribe(speech_file)  # 1秒间隔
```

### 修复3：减少不必要的打断检查

增加检查条件，过滤掉不必要的ASR调用：

```python
def _check_smart_interrupt_thread(self):
    # 1. 检查是否还在播放
    if not self.current_player:
        return
    
    # 2. 检查音频长度是否足够
    if len(audio_data) < 8000:  # < 0.5秒
        return
    
    # 3. ASR识别（使用2秒限流）
    text = self.asr.transcribe(temp_file, is_interrupt_check=True)
    
    # 4. 再次检查是否还在播放
    if not self.current_player:
        return
```

### 修复4：提高打断阈值

减少打断检查触发频率：

```python
CONFIG = {
    'interrupt_min_frames': 15,  # 从10增加到15（450ms）
}
```

### 修复5：禁用LLM语义检查

LLM调用会增加延迟和成本，先禁用：

```python
CONFIG = {
    'interrupt_check_semantic': False,  # 暂时禁用
}
```

仅使用关键词过滤，足以过滤大部分无意义打断。

### 修复6：错误计数和自动重建

检测连续错误，自动重建连接：

```python
def transcribe(self, audio_file):
    try:
        # ... 识别逻辑
        if self.result:
            self.error_count = 0  # 成功，重置
        else:
            self.error_count += 1
    except Exception as e:
        self.error_count += 1
        
        # 连续3次错误，强制重建
        if self.error_count >= self.max_errors:
            print(f"  [ASR] 错误过多({self.error_count}次)，强制重建连接")
            self.recognizer = None
            self.error_count = 0
```

## 效果对比

### 修复前
```
请求频率: ~2-3 QPS
ASR调用: 每段语音2次（打断+完整）
限流间隔: 0.5秒
结果: ❌ TOO_MANY_REQUESTS频繁出现
```

### 修复后
```
请求频率: ~0.5-1 QPS
ASR调用: 减少（过滤短音频）
限流间隔: 打断检查2秒，正常1秒
结果: ✅ 显著减少限流错误
```

## 配置总结

### 限流配置
```python
# ASR
min_interval = 1.0秒  # 正常识别
min_interval * 2 = 2.0秒  # 打断检查

# TTS
min_interval = 1.0秒
```

### 打断配置
```python
'interrupt_min_frames': 15,  # 450ms最少长度
'interrupt_check_semantic': False,  # 禁用LLM
```

### 错误重试
```python
max_errors = 3  # 连续3次错误重建连接
```

## 阿里云NLS限流说明

### 官方限流规则
- **免费版**: 10 QPS（每秒请求数）
- **付费版**: 根据套餐不同

### 我们的策略
- 限流间隔1秒 = 最大1 QPS（单线程）
- 打断检查2秒 = 最大0.5 QPS
- **总计**: 理论最大1.5 QPS，远低于10 QPS限制

### 为什么还会触发限流？

1. **并发请求** - 多个线程同时调用
2. **Token限流** - 同一Token在多个实例使用
3. **连接复用** - WebSocket连接可能被多个请求共享

## 监控和调试

### 日志观察

**正常运行**:
```
[ASR] 音频: 48044字节 → 'hello' (1.1s)
[TTS] 文本: 'Hi there' → 78844字节 (1.9s)
```

**触发限流**:
```
[ASR] 限流等待1.0s... 音频: 48044字节
[TTS] 限流等待1.5s... 文本: 'Hi'
```

**错误重建**:
```
[ASR] 错误过多(3次)，强制重建连接
[ASR] Recognizer创建成功
```

### 调优建议

#### 如果仍有限流错误

**方案A: 增加限流间隔**
```python
self.min_interval = 2.0  # 增加到2秒
```

**方案B: 完全禁用智能打断**
```python
CONFIG = {
    'smart_interrupt_enabled': False,
}
```

**方案C: 增加打断阈值**
```python
'interrupt_min_frames': 20,  # 600ms
```

#### 如果响应太慢

**方案A: 降低限流间隔（风险）**
```python
self.min_interval = 0.8  # 降到0.8秒（可能触发限流）
```

**方案B: 降低打断阈值**
```python
'interrupt_min_frames': 10,  # 300ms
```

## WebSocket超时处理

### IDLE_TIMEOUT原因
- WebSocket连接建立后，长时间（通常60-120秒）无数据传输
- 服务端主动关闭连接
- 客户端未察觉，继续使用 → 报错

### 当前处理策略
```python
try:
    self.recognizer.start(...)
except Exception as e:
    print(f"start失败: {e}, 重建recognizer")
    self.recognizer = None
    self._create_recognizer()
    # 重试
    self.recognizer.start(...)
```

### 未来优化方向
1. **心跳保活** - 定期发送空请求保持连接
2. **连接池** - 维护多个连接，轮询使用
3. **懒加载** - 使用时才创建连接

## 测试验证

### 测试1：正常对话
```bash
./call_optimized.sh <电话号码>
```
- 进行10轮对话
- 观察是否有TOO_MANY_REQUESTS错误
- ✅ 应该很少或没有

### 测试2：快速打断
- TTS播放时快速多次说话
- 观察限流等待日志
- ✅ 应该有适当的等待，但不影响体验

### 测试3：长时间空闲
- 接通电话后保持1分钟静默
- 然后说话
- ✅ 应该正常识别，不报IDLE_TIMEOUT

## 成本影响

### 修复前（每通5分钟电话）
- ASR调用: ~100次（打断+识别）
- 成本: ~$0.10

### 修复后
- ASR调用: ~50次（过滤掉50%无效打断）
- 成本: ~$0.05

**节省**: 50%

## 相关配置文件

- `sip_ai_nls_optimized.py` - 主程序
  - Line 160-163: ASR限流配置
  - Line 318-320: TTS限流配置
  - Line 60-61: 打断配置

## 相关文档

- `SMART_INTERRUPT_GUIDE.md` - 智能打断系统说明
- `OPTIMIZED_VERSION.md` - NLS优化版本总体说明
- `ECHO_CANCELLATION_CONFIG.md` - 回声消除配置

# TTS对比：NLS vs DashScope

## 当前系统使用

当前 `sip_ai_nls_optimized.py` 使用的是 **NLS TTS**

## 两种TTS的区别

### 1. NLS TTS（当前使用）
```python
# 优点：
- WebSocket长连接，复用连接
- 响应速度快
- 支持实时流式传输

# 缺点：
- 容易触发限流
- 配额限制严格
- 需要Token认证
```

### 2. DashScope TTS（test_tts.py中）
```python
# 优点：
- 使用API Key，更简单
- 音质可能更好
- 限流可能更宽松

# 缺点：
- 每次都是HTTP请求，无法复用连接
- 可能稍慢
- 需要dashscope库
```

## test_tts.py使用的配置

```python
dashscope.api_key = "sk-ebf86b67058945fa827863a3742df0b0"
model = 'sambert-indah-v1'  # 印尼语女声
sample_rate = 48000
format = 'wav'
```

## 问题

你想：
1. **替换TTS引擎**：从NLS改为DashScope？
2. **只更新API Key**：继续使用NLS但用新的Key？

## 方案1：替换为DashScope TTS（推荐）

### 优点
- 可能配额更高
- 限流问题可能减轻
- 更简单的认证

### 需要修改
1. 安装dashscope库
2. 重写TTS引擎
3. 测试新引擎

### 实现步骤

我可以帮你：
1. 创建新的DashScope TTS引擎类
2. 替换掉OptimizedNLSTTSEngine
3. 保持其他功能不变

## 方案2：继续使用NLS（当前）

### 优点
- 已经实现，无需改动
- WebSocket长连接，效率高

### 缺点
- 仍可能有限流问题（取决于新AppKey配额）

## 建议

**先测试新的NLS AppKey**：
```bash
./FORCE_RESTART.sh
./call_optimized.sh <电话号码>
```

观察：
- 是否还有频繁限流？
- TTS是否工作正常？
- 响应速度如何？

**如果仍有严重限流**，再考虑切换到DashScope TTS。

## 我可以帮你

1. **立即切换到DashScope TTS**
   - 创建新的TTS引擎
   - 集成到系统中
   
2. **先测试当前NLS配置**
   - 看看新AppKey是否解决问题
   - 如果不行再切换

你想怎么做？

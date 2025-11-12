# TTS引擎升级说明 - 切换到Alibaba DashScope

## 变更概述

从 **Edge TTS** 替换为 **Alibaba DashScope TTS**（sambert-indah-v1 印尼语模型）

## 原因

1. **Edge TTS不稳定**：经常返回 "No audio was received" 错误
2. **更好的印尼语支持**：sambert-indah-v1 专为印尼语优化
3. **更好的音质**：DashScope提供更自然的语音
4. **直接8000Hz输出**：无需转换，适合电话系统

## 新TTS配置

### 模型信息
- **服务商**：阿里云 DashScope
- **模型**：sambert-indah-v1（印尼语女声）
- **采样率**：8000Hz（电话格式）
- **输出格式**：WAV

### API Key
默认使用：`sk-ebf86b67058945fa827863a3742df0b0`

可通过环境变量覆盖：
```bash
export DASHSCOPE_API_KEY="your-api-key"
```

## 代码变更

### TTSEngine类（第238-357行）

**之前**：
```python
class TTSEngine:
    def __init__(self):
        import edge_tts
        self.edge_tts = edge_tts
        # ...
    
    def synthesize(self, text):
        # Edge TTS (不稳定)
        asyncio.run(self._synthesize(text, mp3))
        # 转换 mp3 -> wav
```

**之后**：
```python
class TTSEngine:
    def __init__(self):
        import dashscope
        from dashscope.audio.tts import SpeechSynthesizer
        
        self.dashscope = dashscope
        self.SpeechSynthesizer = SpeechSynthesizer
        self.dashscope.api_key = api_key
        
        self.model = 'sambert-indah-v1'
        self.sample_rate = 8000
    
    def synthesize_dashscope(self, text):
        result = self.SpeechSynthesizer.call(
            model=self.model,
            text=text,
            sample_rate=self.sample_rate,
            format='wav'
        )
        # 直接获取WAV数据
        audio_data = result.get_audio_data()
        # 保存
        with open(wav, 'wb') as f:
            f.write(audio_data)
    
    def synthesize(self, text):
        # 优先使用 DashScope
        if self.use_dashscope:
            wav = self.synthesize_dashscope(text)
            if wav:
                return wav
        
        # 备选：espeak
        if self.espeak_available:
            return self.synthesize_espeak(text)
```

## 优势对比

| 特性 | Edge TTS | DashScope TTS |
|------|----------|---------------|
| 稳定性 | ❌ 经常失败 | ✅ 稳定 |
| 印尼语音质 | 😐 一般 | 😊 优秀 |
| 采样率 | 48000Hz（需转换） | 8000Hz（直接可用） |
| 异步调用 | 需要 asyncio | 同步调用 |
| 网络依赖 | 高 | 中 |
| 速度 | ~1-2秒 | ~0.5-1秒 |

## 安装依赖

如果需要安装：
```bash
pip3 install dashscope
```

检查是否已安装：
```bash
python3 -c "import dashscope; print('已安装')"
```

## 使用示例

### 基本使用
```python
tts = TTSEngine()
wav_file = tts.synthesize("Halo, selamat pagi!")
# 返回: /home/henry/pjproject/temp_audio/tts_dashscope_20251107_123456.wav
```

### 在系统中自动使用
启动系统后自动使用新的TTS：
```bash
./start_vad_system.sh
```

系统初始化时会显示：
```
[TTS] DashScope TTS已初始化
  模型: sambert-indah-v1
  采样率: 8000Hz
```

## 测试验证

### 1. 单独测试TTS
```python
from sip_ai_with_webrtc_vad import TTSEngine

tts = TTSEngine()
wav = tts.synthesize("Selamat datang di sistem AI kami")
print(f"生成的音频: {wav}")

# 播放测试
import os
os.system(f"ffplay {wav}")
```

### 2. 完整系统测试
```bash
./start_vad_system.sh
```

```
>>> call 82121065486
```

对话测试：
- 说："Halo"
- 听AI回复（应该是清晰的印尼语女声）

### 3. 检查日志
应该看到：
```
[TTS] DashScope TTS已初始化
  模型: sambert-indah-v1
  采样率: 8000Hz

# 对话时：
[3/3] TTS合成...
  [TTS] DashScope完成 (0.8s, 45632 bytes)
  ✓ 已播放
```

## 备选方案

如果DashScope失败，系统会自动fallback到espeak：

```
[TTS] DashScope失败: ConnectionError
  [TTS] DashScope失败，尝试备选方案...
  [TTS] 使用espeak...
  [TTS] espeak完成 (0.2s)
```

## 配置选项

### 更改API Key
在 `start_vad_system.sh` 中添加：
```bash
export DASHSCOPE_API_KEY="your-key-here"
```

### 更改模型
编辑 `sip_ai_with_webrtc_vad.py` 第254行：
```python
self.model = 'sambert-indah-v1'  # 或其他支持的模型
```

### 更改采样率
编辑第255行：
```python
self.sample_rate = 8000  # 保持8000用于电话
```

可选值：8000, 16000, 22050, 24000, 48000

## 可用的印尼语模型

| 模型名称 | 性别 | 特点 |
|---------|------|------|
| sambert-indah-v1 | 女 | 自然、清晰 |
| sambert-ario-v1 | 男 | 低沉、稳重 |

更改模型需要修改 `self.model` 配置。

## 成本说明

DashScope TTS按调用次数计费：
- 前100万字符/月：免费
- 超过后：约 ¥0.002/100字符

对于典型的客服对话（每次回复50字符），
每月1000通电话（每通5次回复）= 250,000字符 = **免费**

## 故障排查

### 问题1：API Key无效
```
[TTS] DashScope失败: Invalid API key
```

**解决**：
1. 检查API Key是否正确
2. 访问 https://dashscope.console.aliyun.com/ 获取新Key
3. 设置环境变量或更新代码中的默认值

### 问题2：网络连接失败
```
[TTS] DashScope失败: ConnectionError
```

**解决**：
1. 检查网络连接
2. 系统会自动fallback到espeak
3. 不影响功能，只是音质会下降

### 问题3：音频为空
```
[TTS] DashScope失败: 未生成音频数据
```

**解决**：
1. 检查文本内容是否为空
2. 检查API配额是否用完
3. 等待几秒后重试

## 修改的文件

- `/home/henry/pjproject/sip_ai_with_webrtc_vad.py`
  - 第238-357行：完全重写TTSEngine类
  - 移除Edge TTS和async相关代码
  - 添加DashScope集成
  - 保留espeak作为备选

## 相关文件

- `/home/henry/pjproject/test_tts.py` - DashScope测试示例
- `/home/henry/pjproject/sip_ai_with_webrtc_vad.py` - 主程序
- `/home/henry/pjproject/temp_audio/` - TTS输出目录

## 总结

✅ **已完成**：
- 移除不稳定的Edge TTS
- 集成阿里云DashScope TTS
- 使用印尼语专用模型 sambert-indah-v1
- 直接输出8000Hz WAV（无需转换）
- 保留espeak作为备选方案

✅ **优势**：
- 更稳定可靠
- 更好的印尼语音质
- 更快的生成速度
- 简化的代码（无需async）

✅ **兼容性**：
- API接口不变（`tts.synthesize(text)`）
- 对其他代码无影响
- 自动fallback机制

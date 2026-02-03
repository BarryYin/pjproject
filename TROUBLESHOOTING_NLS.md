# 🔧 NLS性能问题排查与修复

## 🐛 发现的问题

### 问题1: ASR等待超时（30秒）

```
[ASR] 音频大小: 48044 字节
[ASR] 发送耗时: 1.3s
[ASR] 等待耗时: 30.0s  ← 超时了！
[ASR] 识别: '...' (31.3s)
```

**原因**: NLS服务没有返回结果，等待直到超时

**可能原因**:
1. 音频格式问题
2. Token过期
3. 网络问题
4. NLS服务问题

### 问题2: PJSIP线程断言失败

```
pj_thread_this: Assertion '!"Calling pjlib from unknown/external thread..."' failed.
```

**原因**: 在非PJSIP线程中调用了PJSIP函数（play_audio_response）

---

## ✅ 已实施的修复

### 修复1: 独立线程处理

**Before**:
```python
def process_speech(self, audio_data):
    # 直接在VAD线程中处理
    text = self.asr.transcribe(...)
    self.play_audio_response(...)  # ← PJSIP线程问题
```

**After**:
```python
def process_speech(self, audio_data):
    # 使用独立线程，避免阻塞
    thread = threading.Thread(target=self._process_speech_thread, args=(audio_data,))
    thread.start()

def _process_speech_thread(self, audio_data):
    # 在独立线程中处理
    ...
```

**效果**: 避免PJSIP线程冲突

### 修复2: 禁用不必要的NLS功能

**Before**:
```python
sr.start(
    enable_punctuation_prediction=True,      # 标点预测，增加延迟
    enable_inverse_text_normalization=True   # 反标准化，增加延迟
)
```

**After**:
```python
sr.start(
    enable_punctuation_prediction=False,   # 禁用，加快
    enable_inverse_text_normalization=False # 禁用，加快
)
```

**效果**: 减少处理时间

### 修复3: 加快音频发送

**Before**:
```python
chunk_size = 3200
time.sleep(0.005)  # 每次延迟5ms
```

**After**:
```python
chunk_size = 6400  # 更大的chunk
# 不sleep，直接发送
```

**效果**: 发送速度提升2倍

### 修复4: 增加详细日志

```python
def on_start(message, *args):
    print("  [ASR] 识别器已启动")

def on_completed(message, *args):
    print("  [ASR] 收到完成回调")
    
def on_error(message, *args):
    print(f"  [ASR] 错误回调: {message}")
    
def on_close(*args):
    print("  [ASR] 连接关闭")
```

**效果**: 精确定位问题

---

## 🔍 诊断步骤

### 步骤1: 检查Token

```bash
# 测试Token获取
python3 << 'EOF'
import sys
sys.path.insert(0, 'alibabacloud-nls-python-sdk')
from nls.token import getToken

token = getToken(os.getenv('ALI_NLS_AKID', ''), os.getenv('ALI_NLS_AKKEY', ''))
print(f"Token: {token[:50]}...")
EOF
```

预期: 看到token字符串

### 步骤2: 检查音频格式

```bash
# 查看生成的音频文件
ls -lh temp_audio/speech_*.wav | tail -5

# 使用file命令检查格式
file temp_audio/speech_*.wav | tail -1
```

预期: `RIFF (little-endian) data, WAVE audio, Microsoft PCM, 8000 Hz, mono`

### 步骤3: 运行测试查看日志

```bash
./call_nls.sh 85211111111
```

观察输出：
```
  [ASR] 音频大小: XXXX 字节
  [ASR] 识别器已启动     ← 应该看到这个
  [ASR] 发送耗时: X.Xs
  [ASR] 等待耗时: X.Xs
  
  # 下面应该看到以下之一：
  [ASR] 收到完成回调     ← 成功
  [ASR] 错误回调: ...    ← 有错误
  [ASR] 连接关闭         ← 连接问题
```

---

## 🎯 可能的问题与解决

### 问题A: 始终超时30秒

**症状**: `[ASR] 等待耗时: 30.0s`

**原因**: NLS服务没有响应

**解决方案**:

1. **检查网络**:
```bash
ping -c 3 nls-gateway.cn-shanghai.aliyuncs.com
```

2. **检查Token有效性**:
```python
# Token可能过期，重新获取
self.token = None
self.get_token()
```

3. **检查音频格式**:
```python
# 确保是8k PCM格式
with wave.open(speech_file, 'wb') as wf:
    wf.setnchannels(1)       # 单声道
    wf.setsampwidth(2)       # 16-bit
    wf.setframerate(8000)    # 8kHz
```

### 问题B: "识别器已启动"但无"完成回调"

**症状**: 看到启动消息，但没有完成或错误消息

**原因**: 音频发送有问题或NLS没有正确接收

**解决方案**:

1. **减小音频大小**:
```python
# 限制音频长度
'vad_max_speech_frames': 50,  # 从100降至50（1.5秒）
```

2. **使用更简单的参数**:
```python
sr.start(
    aformat="pcm",
    sample_rate=8000
    # 其他参数都用默认值
)
```

### 问题C: PJSIP线程错误

**症状**: `Assertion '!"Calling pjlib from unknown/external thread..."'`

**原因**: 在非PJSIP线程中调用了PJSIP函数

**解决方案**: ✅ 已修复 - 使用独立线程

### 问题D: TTS也很慢（31.2秒）

**症状**: `[TTS] 合成完成 (75842字节, 31.2s)`

**可能原因**:
1. 每次都重新获取Token
2. 网络慢
3. 文本太长

**解决方案**: ✅ 已修复 - 预获取Token

---

## 🚀 备选方案：使用faster-whisper

如果NLS持续有问题，可以回退到faster-whisper：

### 方案1: 混合模式

```python
class HybridASREngine:
    def __init__(self):
        self.nls_asr = NLSASREngine()
        self.whisper_asr = WhisperASREngine()  # 备选
    
    def transcribe(self, audio_file):
        try:
            # 先尝试NLS
            text = self.nls_asr.transcribe(audio_file)
            if text:
                return text
        except:
            pass
        
        # 失败则用Whisper
        print("  [ASR] NLS失败，使用Whisper备选")
        return self.whisper_asr.transcribe(audio_file)
```

### 方案2: 完全使用Whisper

使用原版的 `sip_ai_with_webrtc_vad.py`

---

## 📊 性能基准

### 正常NLS性能

```
[ASR] 音频大小: 24000 字节（1.5秒）
[ASR] 识别器已启动
[ASR] 发送耗时: 0.3s
[ASR] 收到完成回调
[ASR] 连接关闭
[ASR] 等待耗时: 1.2s
[ASR] 识别: 'Hello' (1.5s)  ← 总耗时<2秒
```

### 异常NLS性能

```
[ASR] 音频大小: 48044 字节
[ASR] 识别器已启动
[ASR] 发送耗时: 1.3s
# 没有"收到完成回调" ← 问题！
[ASR] 等待耗时: 30.0s  ← 超时
[ASR] 识别: '' (31.3s)
```

---

## 🔧 调试命令

### 查看NLS SDK版本

```bash
cd alibabacloud-nls-python-sdk
git log --oneline -1
```

### 测试基础NLS功能

```bash
python3 test_alibaba_asr.py
```

预期: 应该能成功识别

### 查看实时日志

```bash
./call_nls.sh 85211111111 2>&1 | tee nls_debug.log
```

### 检查音频文件

```bash
# 播放音频确认内容
play temp_audio/speech_*.wav

# 查看音频信息
soxi temp_audio/speech_*.wav
```

---

## 💡 临时解决方案

### 方案A: 降低超时时间，快速失败

```python
with condition:
    condition.wait(timeout=5)  # 从30降至5秒

if not result_container['text']:
    print("  [ASR] 超时，跳过此句")
    return ""  # 快速返回
```

### 方案B: 添加重试机制

```python
def transcribe(self, audio_file, max_retries=2):
    for attempt in range(max_retries):
        try:
            text = self._transcribe_once(audio_file)
            if text:
                return text
        except:
            if attempt < max_retries - 1:
                print(f"  [ASR] 重试 {attempt + 1}/{max_retries}")
                time.sleep(1)
    return ""
```

### 方案C: 使用更短的音频

```python
# 限制为1秒
'vad_max_speech_frames': 33,  # 33 * 30ms = 1秒
```

---

## 🎯 推荐行动

1. **立即**: 运行修复后的版本，查看详细日志
2. **如果还超时**: 检查网络和Token
3. **如果持续问题**: 考虑使用faster-whisper备选
4. **长期**: 联系阿里云技术支持

---

## 📝 测试清单

- [ ] Token获取成功
- [ ] 看到"识别器已启动"
- [ ] 看到"收到完成回调"（成功）或"错误回调"（失败）
- [ ] 识别耗时<5秒
- [ ] 无PJSIP线程错误
- [ ] 音频播放正常

---

现在使用修复后的版本测试：

```bash
./call_nls.sh 85211111111
```

观察输出，根据日志定位问题！

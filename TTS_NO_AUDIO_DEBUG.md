# 🔍 TTS无声问题诊断

## 🐛 问题描述

客户反馈：**听不到AI回复**

日志显示：
```
[AI] 回复: 'Halo! Ada yang bisa saya bantu hari ini?'
[TTS] ✓ 完成
[TTS] ⊗ 关闭
```

**但是没有 `[播放]` 相关日志！**

---

## 🔍 问题分析

### 可能原因1: TTS文件生成失败

**症状**: 
- 看到 `[TTS] ✓ 完成`
- 但没有看到 `→ XXX字节` 
- 播放代码没执行

**原因**: `synthesize()` 方法返回了 `None`

**检查**:
```bash
# 查看TTS临时文件
ls -lh temp_audio/tts_*.wav | tail -5

# 应该看到文件，但可能是空的（0字节）
```

### 可能原因2: 文件为空

**症状**: 文件存在但大小为0

**原因**: 
1. `on_data` 回调没执行
2. 文件没有正确关闭
3. 数据没有写入

### 可能原因3: 播放函数异常

**症状**: TTS文件正常，但播放失败

**原因**: PJSIP播放器错误

---

## ✅ 已添加的调试

### 1. 详细的文件检查

```python
if os.path.exists(output_file):
    size = os.path.getsize(output_file)
    if size > 0:
        print(f"→ {size}字节")
        return output_file
    else:
        print(f"→ 文件为空")  # ← 新增
        return None
else:
    print(f"→ 文件不存在")    # ← 新增
    return None
```

### 2. 播放前检查

```python
tts_file = self.tts.synthesize(response)
print(f"  [TTS] 返回文件: {tts_file}")  # ← 新增

if tts_file:
    print(f"  [TTS] 准备播放: {tts_file}")  # ← 新增
    self.play_audio_response(tts_file)
else:
    print(f"  [TTS] ✗ 文件为空，无法播放")  # ← 新增
```

### 3. 文件关闭确认

```python
def _on_completed(self):
    if self.audio_file:
        self.audio_file.flush()  # ← 新增：确保写入
        self.audio_file.close()
        print("  [TTS] ✓ 完成（文件已关闭）")  # ← 新增
```

---

## 🧪 诊断步骤

### 步骤1: 测试基础TTS功能

```bash
cd /home/henry/pjproject
python3 test_nls_tts_quick.py
```

**预期输出**:
```
获取Token...
Token: xyz...
创建合成器...
开始合成...
等待完成..........
✓ 完成
文件大小: 50000 字节
✓ 成功: test_tts_output.wav
```

**如果失败**: NLS TTS服务本身有问题

### 步骤2: 运行优化版并观察

```bash
export OPENAI_API_KEY='your-key'
./call_optimized.sh 85211111111
```

**关键日志要看**:
```
[AI] 回复: 'Halo!'
[TTS] 文本: 'Halo!'  → XXX字节 (X.Xs)  ← 应该看到大小
[TTS] 返回文件: /path/to/tts_xxx.wav   ← 应该有路径
[TTS] 准备播放: /path/to/tts_xxx.wav   ← 应该准备播放
[播放] 正在播放... 完成                ← 应该播放完成
```

### 步骤3: 检查TTS文件

```bash
# 查看最新的TTS文件
ls -lht temp_audio/tts_*.wav | head -5

# 播放测试
play temp_audio/tts_*.wav
```

---

## 🎯 可能的结果

### 结果A: 文件不存在

**日志**:
```
[TTS] ✓ 完成
→ 文件不存在 (X.Xs)
[TTS] 返回文件: None
[TTS] ✗ 文件为空，无法播放
```

**原因**: `on_data` 回调没执行，没有接收到音频数据

**解决**: 检查NLS服务状态，可能是网络或Token问题

### 结果B: 文件为空（0字节）

**日志**:
```
[TTS] ✓ 完成
→ 文件为空 (X.Xs)
[TTS] 返回文件: None
[TTS] ✗ 文件为空，无法播放
```

**原因**: 文件创建了但没有数据

**解决**: 
1. 检查 `on_data` 是否被调用
2. 检查文件权限
3. 检查磁盘空间

### 结果C: 文件正常但不播放

**日志**:
```
[TTS] ✓ 完成（文件已关闭）
→ 50000字节 (1.5s)
[TTS] 返回文件: /path/to/file.wav
[TTS] 准备播放: /path/to/file.wav
[播放] 正在播放... 失败: XXX
```

**原因**: PJSIP播放器问题

**解决**: 
1. 检查音频格式（应该是WAV 8kHz单声道）
2. 检查文件路径是否正确
3. 检查通话是否还在连接

### 结果D: 一切正常

**日志**:
```
[TTS] ✓ 完成（文件已关闭）
→ 50000字节 (1.5s)
[TTS] 返回文件: /path/to/file.wav
[TTS] 准备播放: /path/to/file.wav
[播放] 正在播放... 完成
```

**但客户还是听不到**: 可能是音频路由问题

---

## 🔧 快速修复

### 修复1: 确保文件完整写入

已添加：
```python
self.audio_file.flush()  # 强制写入磁盘
```

### 修复2: 增加等待时间

```python
# 在文件关闭后稍等
time.sleep(0.1)  # 确保文件系统同步
```

### 修复3: 验证文件后再返回

已添加：
```python
# 检查文件大小
if os.path.exists(output_file):
    size = os.path.getsize(output_file)
    if size > 0:
        return output_file
    else:
        return None  # 文件为空不返回
```

---

## 🎯 下一步行动

1. **运行修复后的版本**:
```bash
./call_optimized.sh 85211111111
```

2. **观察新的调试日志**:
- 看 `[TTS] 返回文件:` 的值
- 看是否有 `[播放]` 日志

3. **手动测试TTS文件**:
```bash
ls -lh temp_audio/tts_*.wav
play temp_audio/tts_*.wav
```

4. **如果文件正常但不播放**: 
可能是PJSIP线程问题，尝试：
```python
# 注册当前线程
pj.Lib.instance().thread_register("播放线程")
```

---

## 💡 临时方案

如果TTS持续有问题，可以使用备选方案：

### 方案A: 使用espeak本地TTS

```python
import subprocess

def synthesize_espeak(text):
    output_file = "tts_espeak.wav"
    subprocess.run([
        'espeak',
        '-v', 'id',  # 印尼语
        '-w', output_file,
        text
    ])
    return output_file
```

### 方案B: 使用Edge TTS

```python
import edge_tts

async def synthesize_edge(text):
    tts = edge_tts.Communicate(text, voice="id-ID-ArdiNeural")
    await tts.save("tts_edge.wav")
    return "tts_edge.wav"
```

---

**现在运行修复后的版本，看看详细日志！**

```bash
./call_optimized.sh 85211111111
```

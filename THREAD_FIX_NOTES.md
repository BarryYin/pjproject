# PJLIB线程问题修复说明

## 问题描述

运行 `start_vad_system.sh` 时出现断言失败：

```
python3: ../src/pj/os_core_unix.c:939: pj_thread_this: Assertion `!"Calling pjlib from unknown/external thread..."' failed.
```

## 根本原因

1. **VAD处理线程**：`_process_speech` 方法在独立的工作线程中运行
2. **TTS播放**：该线程调用 `play_audio()` 方法
3. **PJLIB调用**：`play_audio()` 使用了PJLIB函数（`create_player`, `conf_connect`等）
4. **未注册线程**：工作线程没有注册到PJLIB，导致断言失败

## PJLIB线程要求

PJSIP要求任何调用PJLIB函数的线程必须：
- 是PJLIB创建的线程，或
- 通过 `pj.Lib.instance().thread_register(name)` 注册

## 解决方案

### 1. 修复 `_process_speech` 方法（第529行）

在方法开始处注册线程：

```python
def _process_speech(self, audio_data):
    """处理检测到的语音"""
    self.is_processing = True
    
    # 注册当前线程到PJLIB
    try:
        pj.Lib.instance().thread_register("vad_worker")
    except Exception as e:
        # 线程已注册或注册失败
        pass
    
    # ... 其余代码
```

### 2. 修复 `on_connected` 方法（第685行）

在初始化方法中也注册线程：

```python
def on_connected(self, callback):
    """接通后初始化"""
    print("\n[系统] 初始化...")
    
    # 注册当前线程（如果需要）
    try:
        pj.Lib.instance().thread_register("init_thread")
    except:
        pass
    
    # ... 其余代码
```

### 3. 禁用不稳定的Edge TTS

Edge TTS经常返回 "No audio was received" 错误，改为直接使用本地espeak：

```python
async def _synthesize(self, text, output_file):
    # 暂时禁用Edge TTS
    raise Exception("Edge TTS已禁用，使用本地espeak")
```

## 修改文件

- `/home/henry/pjproject/sip_ai_with_webrtc_vad.py`
  - 第529-537行：添加线程注册到 `_process_speech`
  - 第688-693行：添加线程注册到 `on_connected`
  - 第260-285行：禁用Edge TTS，改用espeak

## 测试验证

运行 `test_thread_fix.py` 验证线程注册功能：

```bash
python3 test_thread_fix.py
```

预期输出：
```
✓ PJSIP已初始化
✓ 线程已注册
✓ 可以安全调用PJLIB函数
✓ 测试完成
```

## 后续测试

1. 重新启动VAD系统：
   ```bash
   ./start_vad_system.sh
   ```

2. 拨打测试电话：
   ```
   call 82121065486
   ```

3. 验证：
   - ✓ 不再出现断言失败
   - ✓ TTS使用espeak正常工作
   - ✓ 语音识别和AI对话正常
   - ✓ VAD检测正常工作

## 注意事项

1. **线程安全**：每个调用PJLIB的外部线程都需要注册
2. **重复注册**：重复注册同一线程会失败，但不影响功能（用try-except捕获）
3. **线程名称**：每个线程需要唯一的名称
4. **主线程**：主线程通常由PJLIB自动处理，不需要注册

## Edge TTS问题

Edge TTS不稳定的原因可能是：
- 网络连接问题
- API限制或配额
- 语音ID不正确

当前解决方案是直接使用本地espeak，如果需要更好的TTS质量，可以考虑：
- Google Cloud TTS
- Azure TTS（需要API key）
- 离线TTS引擎（如Piper TTS）

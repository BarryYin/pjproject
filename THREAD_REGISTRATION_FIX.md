# PJSIP 线程注册修复

## 问题描述

系统在运行时出现以下断言失败：

```
python3: ../src/pj/os_core_unix.c:939: pj_thread_this: Assertion `!"Calling pjlib from unknown/external thread. You must " "register external threads with pj_thread_register() " "before calling any pjlib functions."' failed.
Aborted (core dumped)
```

### 崩溃场景

- 当VAD检测到用户说话时，系统尝试打断当前TTS播放
- `vad_process_loop()` 线程调用 `stop_current_playback()`
- `stop_current_playback()` 内部调用PJSIP函数（`conf_disconnect`, `player_destroy`）
- 但VAD线程未注册到PJSIP，导致断言失败并崩溃

## 根本原因

PJSIP要求所有调用其API的线程必须先通过 `pj_thread_register()` 注册。

在 `sip_ai_nls_optimized.py` 中：
- ✅ **播放线程**（`play_loop`）已正确注册
- ❌ **VAD线程**（`vad_process_loop`）未注册，但调用了PJSIP函数

## 解决方案

在 `vad_process_loop()` 方法开头添加线程注册：

```python
def vad_process_loop(self):
    """VAD处理循环"""
    try:
        # 注册线程到PJSIP
        pj.Lib.instance().thread_register("VAD线程")
        print("[VAD] VAD线程已启动")
        
        # ... 其余代码
```

## 修改文件

- `sip_ai_nls_optimized.py` - 第617-650行

## 验证步骤

1. 运行系统拨打电话：
   ```bash
   ./call_optimized.sh <电话号码>
   ```

2. 等待TTS播放时，立即说话触发打断

3. 验证：
   - ✅ 无断言失败
   - ✅ 播放被正常打断
   - ✅ ASR正常识别新的语音
   - ✅ 系统继续正常运行

## 关键要点

⚠️ **重要规则**：任何调用PJSIP API的线程都必须先注册

涉及的PJSIP函数包括但不限于：
- `conf_connect()` / `conf_disconnect()`
- `player_create()` / `player_destroy()`
- `recorder_create()` / `recorder_destroy()`
- `call.hangup()`
- 任何操作媒体端口、会议桥的函数

### 线程注册模式

```python
def some_thread_function(self):
    try:
        # 第一步：注册线程
        pj.Lib.instance().thread_register("线程名称")
        
        # 然后才能调用PJSIP函数
        while self.running:
            # ... 业务逻辑
            pj.Lib.instance().conf_disconnect(...)
    except Exception as e:
        print(f"线程错误: {e}")
```

## 修复2：通话结束后的状态检查

### 问题2：通话结束后仍在处理

```
[状态] DISCONNECTED
[状态] >>> 通话已结束
  [ASR] ✓ 完成
→ '那个电视员' (7.2s)
  [AI] 用户: '那个电视员'
python3: ../src/pjsua-lib/pjsua_aud.c:1133: pjsua_conf_disconnect: Assertion `source >= 0 && sink >= 0' failed.
```

### 原因

- 通话结束后，VAD线程和处理线程仍在运行
- 尝试播放TTS或操作会议桥时，端口已失效
- 导致 `conf_disconnect` 断言失败

### 解决方案

在关键位置添加 `self.connected` 状态检查：

1. **VAD循环** - 跳过已断开的通话
```python
if not self.connected:
    time.sleep(0.5)
    continue
```

2. **语音处理** - 多点检查
```python
# 开始处理前
if not self.connected:
    print("  [处理] 通话已结束，跳过处理")
    return

# ASR前
if not self.connected:
    print("  [处理] 通话已结束，跳过ASR")
    return

# 每个步骤都检查
if text and self.connected:
    # ...
if response and self.connected:
    # ...
if tts_file and self.connected:
    # ...
```

3. **打断检测**
```python
if self.vad.is_speaking and self.current_player and self.connected:
    self.stop_current_playback()
```

## 修复3：录音器断开连接的安全性

### 问题3：通话结束时录音器断开失败

```
[状态] DISCONNECTED
[状态] >>> 通话已结束
python3: ../src/pjsua-lib/pjsua_aud.c:1133: pjsua_conf_disconnect: Assertion `source >= 0 && sink >= 0' failed.
```

### 原因

- `stop_vad_recording()` 尝试断开录音器
- 获取 `call.info().conf_slot` 时通话可能已无效
- 或 conf_slot 已经变成负值（无效）

### 解决方案

1. **改进清理顺序** - 先清理资源再设置状态
```python
elif info.state == pj.CallState.DISCONNECTED:
    print("\n[状态] >>> 通话已结束")
    # 先停止所有线程和清理资源（此时connected还是True）
    self.stop_vad_recording()
    # 最后设置connected为False
    with self.lock:
        self.connected = False
```

2. **安全的录音器断开**
```python
if self.recorder_id is not None:
    try:
        # 检查通话是否还有效
        if self.call.is_valid():
            call_info = self.call.info()
            # 检查conf_slot是否有效（>= 0）
            if call_info.conf_slot >= 0 and self.recorder_id >= 0:
                pj.Lib.instance().conf_disconnect(call_info.conf_slot, self.recorder_id)
    except Exception as e:
        # 忽略断开连接的错误
        pass
```

3. **清理播放器后再清理录音器**
```python
def stop_vad_recording(self):
    # 先清理当前播放
    self.stop_current_playback()
    
    # 停止VAD线程
    self.vad_running = False
    # ...
```

## 测试结果

修复后的系统特性：
- ✅ 支持TTS播放打断
- ✅ 多线程安全运行
- ✅ VAD实时检测
- ✅ 通话结束后正确清理
- ✅ 无崩溃，稳定运行

## 测试场景

1. **正常对话流程**
   - ✅ 用户说话 → VAD检测 → ASR识别 → AI回复 → TTS播放

2. **打断场景**
   - ✅ TTS播放中，用户说话 → 立即停止播放 → 处理新语音

3. **通话结束场景**
   - ✅ ASR/TTS处理中，用户挂断 → 停止所有处理 → 正常退出

## 相关文档

- `CALL_END_CRASH_FIX.md` - 通话结束时的播放器清理修复
- `INTERRUPT_AND_LANGUAGE.md` - 打断检测和语言识别优化
- `OPTIMIZED_VERSION.md` - NLS WebSocket优化版本说明

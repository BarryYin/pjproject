# 通话断开崩溃修复总结

## 问题描述

系统在通话正常结束时出现崩溃：

```
[状态] DISCONNECTED
[状态] >>> 通话已结束
python3: ../src/pjsua-lib/pjsua_aud.c:1133: pjsua_conf_disconnect: Assertion `source >= 0 && sink >= 0' failed.
Aborted (core dumped)
```

## 根本原因

通话结束时的资源清理存在竞态条件和顺序问题：

1. **线程注册缺失** - VAD线程调用PJSIP函数但未注册
2. **状态检查不足** - 通话结束后仍在处理语音和操作会议桥
3. **清理顺序错误** - 先设置 `connected=False`，后清理资源
4. **端口有效性未检查** - 断开连接时未检查 conf_slot 是否有效

## 完整解决方案

### 修复1：注册VAD线程

```python
def vad_process_loop(self):
    try:
        # 注册线程到PJSIP（必须！）
        pj.Lib.instance().thread_register("VAD线程")
        
        while self.vad_running:
            # ... 处理逻辑
```

### 修复2：添加连接状态检查

**VAD循环**
```python
while self.vad_running:
    # 检查通话状态
    if not self.connected:
        time.sleep(0.5)
        continue
```

**语音处理**
```python
def _process_speech_thread(self, audio_data):
    # 开始前检查
    if not self.connected:
        return
    
    # ASR前检查
    if not self.connected:
        return
    
    # 每个步骤检查
    if text and self.connected:
        # AI处理
        if response and self.connected:
            # TTS合成
            if tts_file and self.connected:
                # 播放
```

**打断检测**
```python
if self.vad.is_speaking and self.current_player and self.connected:
    self.stop_current_playback()
```

### 修复3：改进清理顺序

```python
def on_state(self):
    if info.state == pj.CallState.DISCONNECTED:
        print("\n[状态] >>> 通话已结束")
        # 1. 先清理资源（此时connected还是True，可以安全操作）
        self.stop_vad_recording()
        # 2. 最后设置connected为False
        with self.lock:
            self.connected = False
```

### 修复4：安全的录音器断开

```python
def stop_vad_recording(self):
    # 先清理播放器
    self.stop_current_playback()
    
    # 停止线程
    self.vad_running = False
    self.play_running = False
    # ... join线程
    
    # 安全断开录音器
    if self.recorder_id is not None:
        try:
            if self.call.is_valid():
                call_info = self.call.info()
                # 检查端口有效性
                if call_info.conf_slot >= 0 and self.recorder_id >= 0:
                    pj.Lib.instance().conf_disconnect(call_info.conf_slot, self.recorder_id)
        except:
            pass  # 忽略错误
    
    # 销毁录音器
    if self.recorder:
        try:
            pj.Lib.instance().recorder_destroy(self.recorder)
        except:
            pass
        self.recorder = None
        self.recorder_id = None
```

## 关键要点

### PJSIP线程安全规则

⚠️ **所有调用PJSIP API的线程都必须先注册**

```python
pj.Lib.instance().thread_register("线程名称")
```

### 资源清理顺序

1. **先停止所有线程** - 设置标志并 join
2. **清理PJSIP资源** - 断开连接、销毁对象
3. **最后更新状态** - 设置 `connected=False`

### 多线程状态检查

在每个可能耗时的操作前后检查 `self.connected`：
- ASR识别前后
- TTS合成前后  
- 播放操作前后
- 会议桥操作前

### 端口有效性检查

```python
if call_info.conf_slot >= 0 and other_slot >= 0:
    pj.Lib.instance().conf_disconnect(...)
```

## 测试场景

### ✅ 正常对话
- 用户说话 → VAD检测 → ASR → AI → TTS → 播放

### ✅ 播放打断
- TTS播放中 → 用户说话 → 立即停止播放 → 处理新语音

### ✅ 通话结束
- 对话进行中 → 用户挂断 → 清理所有资源 → 正常退出

### ✅ 处理中断开
- ASR/TTS处理中 → 用户挂断 → 跳过后续步骤 → 正常退出

## 修改的文件

- `sip_ai_nls_optimized.py` - 主程序文件

## 修改的方法

1. `vad_process_loop()` - 添加线程注册和状态检查
2. `_process_speech_thread()` - 添加多处状态检查
3. `on_state()` - 改进清理顺序
4. `stop_vad_recording()` - 添加安全检查和清理逻辑

## 验证方法

```bash
./call_optimized.sh <电话号码>
```

**正常结束应该看到：**
```
[状态] DISCONNECTED
[状态] >>> 通话已结束
[录音] 已保存
[退出]
```

**不应该出现：**
- ❌ Assertion failed
- ❌ Aborted (core dumped)
- ❌ Segmentation fault

## 相关文档

- `THREAD_REGISTRATION_FIX.md` - 详细的线程注册修复说明
- `CALL_END_CRASH_FIX.md` - 通话结束时的播放器清理修复
- `OPTIMIZED_VERSION.md` - NLS WebSocket优化版本说明

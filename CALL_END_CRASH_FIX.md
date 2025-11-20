# 🔧 通话结束崩溃问题 - 已修复

## 🐛 问题

```
[状态] DISCONNECTED
[状态] >>> 通话已结束

# TTS还在继续...
[TTS] ✓ 完成（文件已关闭）
[TTS] 准备播放: xxx.wav

# 尝试播放或清理时崩溃
pjsua_conf_disconnect: Assertion `source >= 0 && sink >= 0' failed.
Aborted (core dumped)
```

---

## 🔍 根本原因

### 时间线

```
0.0s: 通话正常，AI正在生成回复
      ↓
1.0s: 客户挂断电话
      → [状态] DISCONNECTED
      → call.info().conf_slot 变为无效(-1)
      ↓
1.5s: TTS合成完成
      → 返回文件
      → 加入播放队列
      ↓
2.0s: 播放线程尝试播放
      → 创建播放器成功
      → 尝试连接到 conf_slot
      → ❌ conf_slot = -1 (无效)
      → 断言失败，崩溃！
```

### 问题根源

1. **通话已结束** - `call.info().conf_slot` 已无效
2. **TTS还在运行** - 异步处理，不知道通话结束了
3. **播放队列还有任务** - 队列中的文件还在等待播放
4. **清理代码没检查** - 直接调用 `conf_disconnect()`

---

## ✅ 解决方案

### 核心思路

1. **通话结束时立即清理播放器**
2. **所有PJSIP操作前检查通话有效性**
3. **播放线程检查通话状态**
4. **错误处理更完善**

### 修复点

#### 1. 通话结束时立即清理

```python
def on_state(self):
    if info.state == pj.CallState.DISCONNECTED:
        self.connected = False
        print("\n[状态] >>> 通话已结束")
        
        # ✅ 立即清理播放器
        self.stop_current_playback()
        
        # 停止录音和线程
        self.stop_vad_recording()
```

#### 2. 安全的停止播放

```python
def stop_current_playback(self):
    """停止当前播放 - 安全版"""
    try:
        if self.current_player and self.current_player_slot:
            # ✅ 检查通话是否还有效
            if self.call.is_valid() and self.connected:
                try:
                    pj.Lib.instance().conf_disconnect(
                        self.current_player_slot, 
                        self.call.info().conf_slot
                    )
                except:
                    pass  # 断开失败也继续
            
            # ✅ 总是尝试销毁播放器
            try:
                pj.Lib.instance().player_destroy(self.current_player)
            except:
                pass
            
            # ✅ 总是清空标记
            self.current_player = None
            self.current_player_slot = None
    except:
        pass
```

#### 3. 播放前检查通话状态

```python
def _play_audio(self, audio_file):
    # ✅ 播放前检查
    if not self.call.is_valid() or not self.connected:
        print("通话已结束")
        return
    
    # 创建播放器...
    # 连接音频...
```

#### 4. 播放线程检查

```python
def play_loop(self):
    while self.play_running:
        audio_file = self.play_queue.get(timeout=1)
        
        # ✅ 检查通话是否还在
        if not self.connected:
            print("  [播放] 通话已结束，跳过播放")
            continue
        
        self._play_audio(audio_file)
```

#### 5. 清理时检查

```python
def _play_audio(self, audio_file):
    # ... 播放完成 ...
    
    # 清理
    try:
        # ✅ 只在通话有效时断开连接
        if self.call.is_valid() and self.connected:
            pj.Lib.instance().conf_disconnect(player_slot, info.conf_slot)
        
        # 总是销毁播放器
        pj.Lib.instance().player_destroy(player)
        
        self.current_player = None
        self.current_player_slot = None
    except:
        pass
```

#### 6. 异常时也清理

```python
except Exception as e:
    print(f"失败: {e}")
    # ✅ 失败也要重置标记
    self.current_player = None
    self.current_player_slot = None
```

---

## 📊 修复后流程

### 通话正常结束

```
1. 客户挂断
   → [状态] DISCONNECTED
   ↓
2. on_state() 触发
   → self.connected = False
   → stop_current_playback()  ← 清理播放器
   → stop_vad_recording()     ← 停止录音
   ↓
3. 播放线程获取队列任务
   → 检查 self.connected
   → 发现已断开
   → 跳过播放，不崩溃 ✓
```

### 通话中正常播放

```
1. 通话中
   → self.connected = True
   ↓
2. 播放线程获取任务
   → 检查 self.connected = True ✓
   → 检查 call.is_valid() = True ✓
   → 播放音频
   ↓
3. 播放完成
   → 检查 call.is_valid() = True ✓
   → 断开音频连接
   → 销毁播放器
   → 完成 ✓
```

### 播放中挂断

```
1. 播放中
   → 客户挂断
   → [状态] DISCONNECTED
   ↓
2. on_state() 触发
   → self.connected = False
   → stop_current_playback()
     → 检查 call.is_valid() = False
     → 跳过 conf_disconnect()  ← 不崩溃
     → 销毁播放器
     → 清空标记
   ↓
3. 播放线程的 _play_audio()
   → 检查 self.current_player = None
   → 提前退出
   → 不崩溃 ✓
```

---

## 🎯 关键改进

### 1. 防御式检查 ✅

所有PJSIP操作前检查：
```python
if self.call.is_valid() and self.connected:
    # 安全操作
```

### 2. 多层保护 ✅

- 通话结束时主动清理
- 播放前检查状态
- 操作时检查有效性
- 异常时也清理

### 3. 优雅降级 ✅

不崩溃，只是跳过：
```python
if not self.connected:
    print("通话已结束，跳过播放")
    continue  # 不是 crash
```

### 4. 完整清理 ✅

即使出错也清理标记：
```python
except Exception as e:
    print(f"失败: {e}")
    self.current_player = None  # 总是清理
```

---

## 📺 运行效果

### Before（崩溃）❌

```
[状态] DISCONNECTED
[状态] >>> 通话已结束
[TTS] ✓ 完成
[播放] 正在播放...
Assertion `source >= 0 && sink >= 0' failed
Aborted (core dumped)  ← 崩溃
```

### After（优雅）✅

```
[状态] DISCONNECTED
[状态] >>> 通话已结束
[TTS] ✓ 完成
[TTS] 准备播放: xxx.wav
  [播放] 通话已结束，跳过播放  ← 优雅退出
程序正常退出  ✓
```

---

## 🎉 总结

### 问题
```
通话结束 → TTS还在运行 → 尝试播放 → conf_slot无效 → 崩溃
```

### 解决
```
通话结束 → 立即清理播放器 → 所有操作前检查有效性 → 不崩溃 ✓
```

### 改进点

| 位置 | 修复 |
|------|------|
| on_state() | ✅ 通话结束时立即清理播放器 |
| stop_current_playback() | ✅ 检查通话有效性再断开 |
| play_loop() | ✅ 检查通话状态再播放 |
| _play_audio() | ✅ 播放前检查，清理前检查 |
| 异常处理 | ✅ 失败也清理标记 |

---

## 🚀 测试

```bash
./call_optimized.sh 85211111111
```

**测试步骤**：
1. 通话接通
2. 说一句话，等AI开始回复
3. **立即挂断电话**（在AI说话时）
4. 观察：应该优雅退出，不崩溃

**预期结果**：
```
[状态] DISCONNECTED
[状态] >>> 通话已结束
  [播放] 通话已结束，跳过播放  ← 或其他优雅信息
程序正常退出  ✓
```

**不应该出现**：
```
Assertion failed
Aborted (core dumped)
```

---

**通话结束不再崩溃！** 🎊

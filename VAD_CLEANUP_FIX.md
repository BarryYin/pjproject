# VAD线程清理修复说明

## 问题描述

客户挂断电话后，VAD线程没有正确停止，继续尝试读取已关闭的录音文件：

```
[VAD] 已接收 4096 字节音频数据...
[VAD] 已接收 4096 字节音频数据...
(无限循环)
```

## 根本原因

1. **清理顺序问题**：`cleanup()` 只设置了 `self.vad_running = False`，但没有等待VAD线程退出
2. **标志位不一致**：`self.connected` 和 `self.vad_running` 可能不同步
3. **资源未释放**：录音器和播放器没有被正确销毁，文件句柄可能泄漏
4. **退出检查不足**：VAD循环没有充分检查退出条件

## 解决方案

### 1. 改进 `on_state()` - 确保标志位同步

**位置**：第435-449行

**修改**：
```python
elif info.state == pj.CallState.DISCONNECTED:
    print("  ✓ 通话结束，清理资源...")
    self.connected = False  # 先设置为False，停止VAD循环
    self.cleanup()
```

**说明**：在调用 `cleanup()` 之前先设置 `self.connected = False`，立即停止VAD循环。

### 2. 完全重写 `cleanup()` - 正确清理所有资源

**位置**：第628-670行

**新增功能**：

1. **等待VAD线程退出**
   ```python
   if self.vad_thread and self.vad_thread.is_alive():
       self.vad_thread.join(timeout=2.0)
   ```

2. **销毁录音器**
   ```python
   pj.Lib.instance().recorder_destroy(self.recorder)
   self.recorder = None
   ```

3. **销毁播放器**
   ```python
   pj.Lib.instance().player_destroy(self.player)
   self.player = None
   ```

4. **详细日志**
   - 每个步骤都有日志输出
   - 便于调试和监控

### 3. 改进 VAD循环 - 增加退出检查

**位置**：第497-560行

**新增功能**：

1. **循环内退出检查**
   ```python
   if not self.vad_running or not self.connected:
       print("[VAD] 收到退出信号")
       break
   ```

2. **无数据计数器**
   ```python
   no_data_count = 0
   if new_data:
       no_data_count = 0
   else:
       no_data_count += 1
       if no_data_count > 50 and not self.connected:
           break
   ```

3. **异常处理改进**
   ```python
   except Exception as e:
       if not self.connected or not self.vad_running:
           print("[VAD] 连接已断开，正常退出")
           break
   ```

## 清理流程

```
客户挂断
    ↓
on_state() 检测到 DISCONNECTED
    ↓
设置 self.connected = False
    ↓
调用 cleanup()
    ↓
设置 self.vad_running = False
    ↓
VAD循环检测到退出信号
    ↓
VAD循环退出 (break)
    ↓
VAD线程终止
    ↓
cleanup() 等待线程join (最多2秒)
    ↓
断开录音器连接
    ↓
销毁录音器
    ↓
销毁播放器
    ↓
完成清理
```

## 修改文件

- `/home/henry/pjproject/sip_ai_with_webrtc_vad.py`
  - 第447-448行：on_state() 添加 connected = False
  - 第497-560行：_vad_loop() 改进退出逻辑
  - 第628-670行：cleanup() 完全重写

## 测试验证

### 启动系统
```bash
./start_vad_system.sh
```

### 拨打测试电话
```
>>> call 82121065486
```

### 对话后挂断
等待客户或AI对话完成后，挂断电话。

### 检查日志
应该看到完整的清理过程：

```
[呼叫] DISCONNECTED
  ✓ 通话结束，清理资源...
  [清理] 停止VAD线程...
  [清理] 等待VAD线程退出...
[VAD] 收到退出信号
[VAD] 线程退出 (共处理 123 次数据)
  [清理] ✓ VAD线程已退出
  [清理] 断开录音器...
  [清理] 销毁录音器...
  [清理] ✓ 录音器已清理
  [清理] 停止播放器...
  [清理] ✓ 播放器已清理
  [清理] ✓ 所有资源已清理
```

### 验证点

1. ✓ VAD线程快速退出（2秒内）
2. ✓ 不再有无限的"已接收 4096 字节"消息
3. ✓ 所有资源被正确清理
4. ✓ 录音文件正确保存
5. ✓ 可以立即拨打下一个电话

## 技术细节

### 线程同步

使用双重标志位确保线程退出：
- `self.connected`：呼叫状态
- `self.vad_running`：VAD运行状态

两个标志都设为 False 时，VAD循环必定退出。

### 超时保护

```python
self.vad_thread.join(timeout=2.0)
```

最多等待2秒。如果线程卡住，不会无限等待。

### 资源销毁顺序

1. 停止VAD线程（停止数据读取）
2. 断开conference连接
3. 销毁录音器（关闭文件）
4. 销毁播放器（释放音频资源）

### 防御性编程

所有PJLIB调用都包在 try-except 中：
```python
try:
    pj.Lib.instance().recorder_destroy(self.recorder)
except Exception as e:
    print(f"错误: {e}")
```

即使某个步骤失败，不影响其他清理。

## 潜在问题和解决

### 1. VAD线程卡在文件读取

**解决**：
- 添加 `no_data_count` 计数器
- 2.5秒无数据自动退出

### 2. 录音文件损坏

**解决**：
- 先断开连接
- 再销毁录音器
- 确保WAV头正确写入

### 3. 内存泄漏

**解决**：
- 显式销毁所有PJLIB对象
- 设置引用为 None
- Python GC会回收

### 4. 下次呼叫失败

**解决**：
- 完整清理所有资源
- 每次呼叫重新初始化
- 不复用recorder/player

## 相关文件

- `sip_ai_with_webrtc_vad.py` - 主程序
- `THREAD_FIX_NOTES.md` - 线程注册修复
- `DUAL_RECORDING_FIX.md` - 双向录音修复

## 总结

通过改进清理流程和VAD循环退出逻辑，现在可以确保：
1. 挂断后VAD线程立即收到退出信号
2. 线程在2秒内干净退出
3. 所有PJLIB资源被正确释放
4. 录音文件完整保存
5. 系统可以立即处理下一个呼叫

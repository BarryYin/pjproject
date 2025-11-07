# 双向录音修复说明

## 问题描述

客户能听到AI的声音，但录音文件中只有客户的声音，没有AI的回复。

## 原因分析

原来的录音配置只连接了一个音频流：

```python
# 只录制客户的声音
pj.Lib.instance().conf_connect(info.conf_slot, self.recorder_id)
```

### PJSIP Conference Bridge架构

```
┌──────────────────────────────────────┐
│    PJSIP Conference Bridge (混音器)   │
├──────────────────────────────────────┤
│  Slot 0: 本地设备（扬声器/话筒）       │
│  Slot N: 远端呼叫 (客户)              │
│  Slot M: 播放器 (AI音频)              │
│  Slot R: 录音器                       │
└──────────────────────────────────────┘
```

**原始连接**：
```
客户(N) ──→ 录音器(R)  ✓ 录制客户声音
播放器(M) ──→ 客户(N)   ✓ 客户听到AI
播放器(M) ──X 录音器(R)  ✗ 没有录制AI声音
```

## 解决方案

连接两个音频流到录音器：

1. **客户的声音** - `info.conf_slot` → 录音器
2. **AI的声音** - Slot 0 → 录音器

### 修改后的连接

```python
# 连接双向音频到录音器
# 1. 客户的声音（远端）
pj.Lib.instance().conf_connect(info.conf_slot, self.recorder_id)
# 2. 本地播放的声音（AI回复）- 从slot 0连接
pj.Lib.instance().conf_connect(0, self.recorder_id)
```

**新的连接图**：
```
客户(N) ──→ 录音器(R)  ✓ 录制客户声音
Slot 0  ──→ 录音器(R)  ✓ 录制AI声音
播放器(M) ──→ 客户(N)   ✓ 客户听到AI
```

## 修改内容

### 1. start_vad_recording() 方法（第456-475行）

**之前**：
```python
def start_vad_recording(self):
    """开始VAD录音"""
    # ...
    # 连接音频
    pj.Lib.instance().conf_connect(info.conf_slot, self.recorder_id)
    print(f"  [录音] 开始: {os.path.basename(self.record_file)}")
```

**之后**：
```python
def start_vad_recording(self):
    """开始VAD录音 - 双向录制（客户+AI）"""
    # ...
    # 连接双向音频到录音器
    # 1. 客户的声音（远端）
    pj.Lib.instance().conf_connect(info.conf_slot, self.recorder_id)
    # 2. 本地播放的声音（AI回复） - 从slot 0连接
    pj.Lib.instance().conf_connect(0, self.recorder_id)
    print(f"  [录音] 开始双向录制: {os.path.basename(self.record_file)}")
```

### 2. cleanup() 方法（第628-638行）

**之前**：
```python
def cleanup(self):
    """清理资源"""
    self.vad_running = False
    
    if self.recorder:
        try:
            info = self.call.info()
            pj.Lib.instance().conf_disconnect(info.conf_slot, self.recorder_id)
        except:
            pass
```

**之后**：
```python
def cleanup(self):
    """清理资源"""
    self.vad_running = False
    
    if self.recorder:
        try:
            info = self.call.info()
            # 断开双向录音连接
            pj.Lib.instance().conf_disconnect(info.conf_slot, self.recorder_id)
            pj.Lib.instance().conf_disconnect(0, self.recorder_id)
        except:
            pass
```

## 测试验证

### 启动系统
```bash
./start_vad_system.sh
```

### 拨打测试电话
```
>>> call 82121065486
```

### 测试对话
1. 客户说："Halo"
2. AI回复："Halo, saya asisten virtual..."
3. 继续对话...

### 检查录音文件
```bash
# 找到最新的录音
ls -lt recordings/vad_*.wav | head -1

# 播放录音
ffplay recordings/vad_20251107_xxxxxx.wav

# 或使用分析工具
python3 analyze_recording.py
```

### 预期结果
录音文件应该包含：
- ✓ 客户的声音
- ✓ AI的回复声音
- ✓ 完整的双向对话

## 技术细节

### Conference Bridge Slot说明

| Slot | 用途 | 说明 |
|------|------|------|
| 0 | 本地设备 | 扬声器和话筒 |
| info.conf_slot | 远端呼叫 | 客户的音频流 |
| player_id | 播放器 | AI生成的音频 |
| recorder_id | 录音器 | 录制的目标 |

### 音频流向

```
[客户] ←──双向通话──→ [PJSIP]
                        ↓
              [Conference Bridge]
                   ↓     ↓
              [播放器] [录音器]
                   ↓       ↑
               [AI音频]    ↑
                           ↑
                   [混音后的双向音频]
```

### 为什么连接Slot 0？

当播放器播放AI音频时：
```
播放器 → Slot 0 → 客户
```

所以要录制AI的声音，需要从Slot 0获取，因为它包含了所有发送给客户的音频。

## 潜在问题和解决方案

### 1. 回声问题
如果出现回声，可能是因为录音中包含了客户自己的声音。

**解决方案**：
- PJSIP已内置回声消除（AEC）
- 如果仍有问题，可调整AEC参数

### 2. 音量不平衡
客户声音和AI声音可能音量不同。

**解决方案**：
```python
# 在play_audio中调整音量
pj.Lib.instance().conf_adjust_tx_level(self.player_id, 1.5)  # 增加50%
```

### 3. 音频延迟
混音可能引入轻微延迟。

**解决方案**：
- 已经是最优配置
- PJSIP的延迟通常在10-30ms，可接受

## 相关文件

- `/home/henry/pjproject/sip_ai_with_webrtc_vad.py` - 主程序
- `/home/henry/pjproject/recordings/` - 录音保存目录
- `/home/henry/pjproject/THREAD_FIX_NOTES.md` - 线程修复说明

## 总结

通过添加第二个conference bridge连接（Slot 0 → 录音器），现在可以录制完整的双向对话，包括客户和AI的所有声音。

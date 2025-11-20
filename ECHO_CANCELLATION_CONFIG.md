# 回声消除配置指南

## 问题描述

客户在通话时听到回声（echo），影响通话质量。

## 回声产生原因

回声通常由以下原因产生：

1. **声学回声** - 扬声器播放的声音被麦克风再次捕获
2. **网络延迟** - 音频传输延迟导致回声效果
3. **音频反馈** - TTS播放的声音被录音系统捕获并发送回去

## 解决方案

### 1. 启用PJSIP内置回声消除（AEC）

PJSIP提供了强大的回声消除功能，基于Speex AEC算法。

#### 配置参数

```python
media_cfg = pj.MediaConfig()

# 回声尾长（毫秒）- 关键参数！
media_cfg.ec_tail_len = 400

# 回声消除选项
media_cfg.ec_options = 0

# 禁用内置VAD（我们使用WebRTC VAD）
media_cfg.no_vad = True
```

#### ec_tail_len（回声尾长）参数说明

这是**最重要的参数**，决定了AEC可以处理的最大回声延迟：

| 值 | 说明 | 适用场景 |
|---|---|---|
| **0** | 禁用回声消除 | ❌ 不推荐 |
| **200** | 短尾长 | 近距离对话，低延迟网络 |
| **400** | 标准配置 ✅ | **大多数情况（推荐）** |
| **800** | 长尾长 | 高延迟网络，大房间 |
| **1000+** | 超长尾长 | 极高延迟，但消耗更多CPU |

**推荐值：400ms** - 在效果和性能之间取得良好平衡

#### ec_options（回声消除算法）

| 值 | 说明 |
|---|---|
| **0** | Speex AEC（默认）✅ |
| **1** | WebRTC AEC（需编译时启用）|

### 2. 修改位置

在 `sip_ai_nls_optimized.py` 的 `main()` 函数中：

```python
def main():
    # ...
    
    media_cfg = pj.MediaConfig()
    media_cfg.clock_rate = 8000
    media_cfg.audio_frame_ptime = 20
    
    # 启用回声消除 - 400ms尾长
    media_cfg.ec_tail_len = 400
    media_cfg.ec_options = 0
    media_cfg.no_vad = True
    
    lib.init(ua_cfg, log_cfg, media_cfg)
    # ...
```

### 3. 验证配置

启动系统时会看到：

```
======================================================================
  AI对话系统 - NLS优化版（长连接）
======================================================================
  特性: WebSocket长连接复用，极速ASR/TTS
  回声消除: 已启用 (400ms尾长)
======================================================================
```

## 高级调优

### 如果回声仍然存在

#### 选项1：增加回声尾长

```python
media_cfg.ec_tail_len = 800  # 增加到800ms
```

#### 选项2：调整音频帧大小

```python
media_cfg.audio_frame_ptime = 20  # 保持20ms
```

#### 选项3：检查录音和播放设备

确保：
- 录音不会捕获TTS播放的音频
- 使用耳机而非扬声器（如果可能）
- 降低扬声器音量

### 如果CPU占用过高

```python
media_cfg.ec_tail_len = 200  # 降低到200ms
```

## 其他回声消除方法

### 方法1：音频路由隔离（推荐）

当前系统使用PJSIP的会议桥：
- 录音器捕获对方声音
- 播放器发送TTS音频

这种架构下，PJSIP的AEC会自动处理回声。

### 方法2：降低TTS播放音量

在 `_play_audio()` 方法中，可以调整播放音量：

```python
# 通过会议桥调整音量
pj.Lib.instance().conf_adjust_tx_level(player_slot, 0.8)  # 80%音量
```

### 方法3：增加延迟检测

在打断检测中增加延迟，避免误识别TTS回声为用户语音：

```python
# 当前配置
'vad_silence_frames': 15,     # 1.5秒静音后结束
'vad_min_speech_frames': 3,   # 最少0.3秒才算有效语音
```

增加 `vad_min_speech_frames` 可以过滤掉短暂的回声。

## 测试方法

### 测试1：基本通话测试

```bash
./call_optimized.sh <电话号码>
```

- 等待TTS播放
- 保持安静，听是否有回声
- 如果听到自己之前说的话 = 有回声

### 测试2：打断测试

- TTS播放时说话
- 检查是否会误触发（TTS音频被识别为用户语音）
- 正常情况：只有真实用户语音才会打断

### 测试3：长时间通话测试

- 进行多轮对话
- 检查回声是否累积
- 监控CPU占用

## 性能影响

| ec_tail_len | CPU占用 | 内存占用 | 回声消除效果 |
|-------------|---------|----------|-------------|
| 0 (禁用)     | 最低    | 最低     | ❌ 无        |
| 200ms       | 低      | 低       | ⭐⭐⭐       |
| 400ms ✅    | 中      | 中       | ⭐⭐⭐⭐      |
| 800ms       | 高      | 高       | ⭐⭐⭐⭐⭐    |

**推荐配置：400ms** - 99%的场景下足够

## 常见问题

### Q: 启用AEC后仍有回声？

A: 尝试以下步骤：
1. 增加 `ec_tail_len` 到 800
2. 检查是否有多个音频流
3. 确认网络延迟不超过1秒
4. 使用耳机测试

### Q: AEC导致语音失真？

A: 降低 `ec_tail_len` 到 200 或调整 `ec_options`

### Q: CPU占用太高？

A: 降低 `ec_tail_len` 到 200 或禁用（设为0）

### Q: 如何判断AEC是否工作？

A: 
- 看启动信息是否显示"回声消除: 已启用"
- 使用扬声器模式测试（应该没有明显回声）
- 播放TTS时保持安静，看是否误触发VAD

## 相关配置

### WebRTC VAD配置

```python
CONFIG = {
    'vad_aggressiveness': 1,      # 1=低灵敏度（推荐）
    'vad_frame_duration': 30,     # 30ms帧
    'vad_silence_frames': 15,     # 450ms静音后结束
    'vad_min_speech_frames': 3,   # 90ms最少语音长度
}
```

**建议**：如果回声问题严重，可以增加 `vad_min_speech_frames` 到 5-10，过滤掉短暂的回声片段。

## 总结

✅ **已启用配置：**
- `ec_tail_len = 400` - 标准回声消除
- `ec_options = 0` - Speex AEC算法
- `no_vad = True` - 使用WebRTC VAD

✅ **效果：**
- 消除声学回声
- 减少音频反馈
- 改善通话质量

✅ **测试：**
```bash
./call_optimized.sh <电话号码>
```

观察客户是否还能听到回声。如果仍有问题，可以调整 `ec_tail_len` 参数。

## 相关文档

- `OPTIMIZED_VERSION.md` - 系统优化说明
- `THREAD_REGISTRATION_FIX.md` - 线程安全修复
- `CALL_DISCONNECT_FIX_SUMMARY.md` - 通话断开修复

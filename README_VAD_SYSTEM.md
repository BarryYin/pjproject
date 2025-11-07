# WebRTC VAD AI对话系统使用说明

## 🚀 快速开始

### 1. 启动系统（终端1）

```bash
cd /home/henry/pjproject
./start_vad_system.sh
```

等待看到：
```
✓ 系统启动
✓ 传输: xxx.xxx.xxx.xxx:xxxxx
[系统] ✓ 就绪，等待语音输入...
```

### 2. 发起呼叫（终端2）

```bash
./test_vad_call.sh <电话号码>
```

例如：
```bash
./test_vad_call.sh 82121065486
```

或直接用curl：
```bash
curl -X POST http://localhost:8090/api/call \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "你的号码"}'
```

---

## 📊 查看日志

**日志在终端1（启动系统的终端）**

你会看到：

```
[呼叫] CONFIRMED
  ✓ 接通

[录音] 开始: vad_20251107_160530.wav
[VAD] ✓ 监听启动
[系统] ✓ 欢迎语已播放
[系统] ✓ 就绪，等待语音输入...

[VAD] 线程运行中...

  [VAD] 🎤 检测到说话          ← 对方开始说话
  
  [VAD] ✓ 句子结束 (帧数:45, 静音:20)  ← 检测到完整句子

============================================================
  🎤 处理语音
============================================================
  [1/3] ASR识别...
  [ASR] 'Halo, apa kabar?' (1.2s)
  👤 用户: Halo, apa kabar?
  
  [2/3] AI生成...
  [AI] 'Halo! Saya baik, terima kasih.' (0.8s)
  🤖 AI: Halo! Saya baik, terima kasih.
  
  [3/3] TTS合成...
  [TTS] 完成 (2.1s)
  ✓ 已播放
============================================================
```

---

## 🎛️ VAD参数说明

如果VAD检测不准确，可以调整参数。

编辑 `sip_ai_with_webrtc_vad.py`，找到 CONFIG：

```python
# WebRTC VAD配置
'vad_aggressiveness': 2,      # 0-3
'vad_frame_duration': 30,     # ms
'vad_silence_frames': 20,     # 连续静音帧数
'vad_min_speech_frames': 5,   # 最少语音帧数
```

### 调整建议

#### 如果VAD太敏感（噪音也触发）
```python
'vad_aggressiveness': 3,        # 改为3（更严格）
'vad_min_speech_frames': 10,   # 增加最少帧数
```

#### 如果VAD不敏感（说话没检测到）
```python
'vad_aggressiveness': 1,        # 改为1（更宽容）
'vad_silence_frames': 15,       # 减少静音阈值
```

#### 如果句子切断太快
```python
'vad_silence_frames': 30,       # 增加到30帧 = 0.9秒
```

#### 如果句子切断太慢
```python
'vad_silence_frames': 15,       # 减少到15帧 = 0.45秒
```

---

## 🔧 常见问题

### Q: 没看到VAD日志？

A: 确认：
1. 电话接通了吗？（看到"[呼叫] CONFIRMED"）
2. 欢迎语播放了吗？（看到"欢迎语已播放"）
3. 对方说话了吗？

### Q: VAD检测不到说话？

A: 可能原因：
1. 音量太小
2. VAD太激进（把语音当静音）
3. 背景噪音干扰

**解决**：调整 `vad_aggressiveness` 为 1 或 0

### Q: VAD误触发（噪音触发）？

A: 调整参数：
```python
'vad_aggressiveness': 3
'vad_min_speech_frames': 10
```

### Q: ASR识别不准？

A: 这是ASR模型问题，与VAD无关。可以：
1. 换更大的Whisper模型（'small' 或 'medium'）
2. 确认对方说的是印尼语

---

## 📁 录音文件

所有通话录音在：
```
/home/henry/pjproject/recordings/vad_*.wav
```

可以事后分析音频，看VAD是否正确分段。

---

## 🎯 测试流程

1. **启动系统**：`./start_vad_system.sh`
2. **发起呼叫**：`./test_vad_call.sh <号码>`
3. **观察日志**：看终端1的输出
4. **对方说话**：说一句印尼语
5. **等待VAD检测**：看是否出现"🎤 检测到说话"
6. **等待处理**：看ASR/AI/TTS流程
7. **听回复**：对方听到AI语音

---

## ✅ 成功标志

看到这些日志说明VAD工作正常：

```
[VAD] 🎤 检测到说话         ← VAD检测到语音
[VAD] ✓ 句子结束            ← VAD判断句子完成
[ASR] '...'                 ← ASR识别成功
[AI] '...'                  ← AI生成回复
[TTS] 完成                  ← TTS合成成功
✓ 已播放                    ← 播放给对方
```

---

## 📞 请告诉我

**你的正确测试号码是什么？**

我会更新脚本中的默认号码。

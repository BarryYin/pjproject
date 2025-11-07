# 🚀 最简单的使用方式

## 一步到位

```bash
cd /home/henry/pjproject
./start_vad_system.sh
```

## 等待启动完成

你会看到：
```
✓ 系统启动
✓ 传输: xxx.xxx.xxx.xxx:xxxxx

命令:
  call <号码> - 拨打电话
  quit       - 退出

>>> 
```

## 输入命令拨号

```
>>> call 82121065486
```

（把 82121065486 换成你的真实号码）

## 观察日志

接通后会自动显示：
```
[呼叫] CONFIRMED
  ✓ 接通

[录音] 开始: vad_xxx.wav
[VAD] ✓ 监听启动
[系统] ✓ 欢迎语已播放
[系统] ✓ 就绪，等待语音输入...

[VAD] 线程运行中...
```

**当对方说话时，会显示：**
```
  [VAD] 🎤 检测到说话
  [VAD] ✓ 句子结束 (帧数:45, 静音:20)
  
  [1/3] ASR识别...
  [ASR] 'Halo, apa kabar?' (1.2s)
  👤 用户: Halo, apa kabar?
  
  [2/3] AI生成...
  [AI] 'Halo! Saya baik.' (0.8s)
  🤖 AI: Halo! Saya baik.
  
  [3/3] TTS合成...
  [TTS] 完成 (2.1s)
  ✓ 已播放
```

## 就这么简单！

1. `./start_vad_system.sh`
2. 输入 `call <号码>`
3. 观察日志
4. 对方说话，系统自动回复

**WebRTC VAD会自动检测语音并触发AI回复！** 🎉

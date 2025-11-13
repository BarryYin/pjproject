# 📞 命令行版本使用指南

## 🎯 纯命令行，无Web界面

如果你不想用Web界面，可以直接在命令行拨打电话！

---

## 🚀 快速使用

### 方法1: 使用快捷脚本（最简单）⭐

```bash
# 1. 设置API Key
export OPENAI_API_KEY='sk-proj-...'

# 2. 拨打电话
./call_nls.sh 85211111111
```

### 方法2: 直接运行Python脚本

```bash
# 1. 设置API Key
export OPENAI_API_KEY='sk-proj-...'

# 2. 拨打电话
python3 sip_ai_nls_cli.py 85211111111
```

---

## 📺 运行效果

启动后你会看到：

```
======================================================================
  AI对话系统 - 阿里云NLS CLI版
======================================================================
  ASR: 阿里云NLS WebSocket
  TTS: 阿里云NLS WebSocket (发音人: indah)
  AI:  OpenAI gpt-3.5-turbo
  VAD: WebRTC (激进度: 2)
======================================================================

[SIP] 账户: 6281479242434
[SIP] 服务器: 147.139.205.88:5060

[拨号] sip:1346285211111111@147.139.205.88
[提示] 按 Ctrl+C 挂断

[状态] CALLING - 183

[状态] CONFIRMED - 200
[状态] >>> 通话已接通，AI对话系统已激活

[录音] recordings/call_nls_20231113_210530.wav

  [VAD] 检测到说话...
  [VAD] 句子结束 (45帧)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [ASR] 识别: 'Halo, apa kabar?' (0.6s)
  [AI]  回复: 'Halo! Saya baik, terima kasih.' (1.0s)
  [TTS] 合成完成 (272442字节, 0.8s)
  [播放] 正在播放AI回复...
  [播放] 完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  [VAD] 检测到说话...
  [VAD] 句子结束 (38帧)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [ASR] 识别: 'Terima kasih, sampai jumpa' (0.5s)
  [AI]  回复: 'Sama-sama! Sampai jumpa!' (0.9s)
  [TTS] 合成完成 (198234字节, 0.7s)
  [播放] 正在播放AI回复...
  [播放] 完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 按 Ctrl+C 挂断

[挂断] 正在挂断电话...

[状态] DISCONNECTED - 200
[状态] >>> 通话已结束
[录音] 已保存: recordings/call_nls_20231113_210530.wav
[退出] 再见！
```

---

## 🎮 操作说明

### 拨打电话

```bash
# 拨打印尼号码
./call_nls.sh 85211111111

# 拨打其他号码
./call_nls.sh 81234567890
```

**注意**: 系统会自动添加前缀 `13462`

### 挂断电话

按 **Ctrl+C** 即可挂断

### 查看录音

```bash
# 查看所有录音
ls -lh recordings/call_nls_*.wav

# 播放最新录音
play $(ls -t recordings/call_nls_*.wav | head -1)
```

---

## 📊 对话过程

每次对话都会显示：

1. **VAD检测**: `[VAD] 检测到说话...` → `[VAD] 句子结束`
2. **ASR识别**: `[ASR] 识别: '文本' (时间)`
3. **AI回复**: `[AI] 回复: '文本' (时间)`
4. **TTS合成**: `[TTS] 合成完成 (大小, 时间)`
5. **播放**: `[播放] 正在播放AI回复...` → `[播放] 完成`

---

## 🔍 与Web版本对比

| 特性 | Web版 | CLI版 |
|------|-------|-------|
| **启动方式** | `./start_nls_integrated.sh` | `./call_nls.sh 号码` |
| **界面** | Web浏览器 | 纯命令行 |
| **拨号** | Web界面输入 | 命令行参数 |
| **状态显示** | 实时Web更新 | 控制台输出 |
| **挂断** | 点击按钮 | Ctrl+C |
| **录音** | 自动保存 | 自动保存 |
| **适用场景** | 演示、多人使用 | 快速测试、自动化 |

---

## 🎯 使用场景

### 场景1: 快速测试

```bash
# 快速拨打测试号码
./call_nls.sh 85211111111

# 说几句话测试
# 按 Ctrl+C 退出
```

### 场景2: 脚本集成

```bash
#!/bin/bash
# 自动拨打多个号码

export OPENAI_API_KEY='...'

for number in 85211111111 85222222222 85233333333; do
    echo "拨打 $number"
    timeout 300 ./call_nls.sh $number
    sleep 10
done
```

### 场景3: 定时任务

```bash
# 添加到crontab
0 9 * * * cd /home/henry/pjproject && ./call_nls.sh 85211111111
```

---

## 📝 文件说明

| 文件 | 大小 | 说明 |
|------|------|------|
| `sip_ai_nls_cli.py` | 18KB | 主程序（无Web界面） |
| `call_nls.sh` | 小 | 快捷拨号脚本 |
| `CLI_USAGE.md` | 本文档 | 使用说明 |

---

## 🆚 选择哪个版本？

### 选择Web版（`sip_ai_nls_integrated.py`），如果你：

- ✅ 需要图形界面
- ✅ 多人共享使用
- ✅ 需要远程访问
- ✅ 演示给他人看

### 选择CLI版（`sip_ai_nls_cli.py`），如果你：

- ✅ 喜欢命令行
- ✅ 需要脚本集成
- ✅ 快速测试
- ✅ 自动化场景

---

## 🛠️ 高级用法

### 修改配置

编辑 `sip_ai_nls_cli.py`，找到 `CONFIG` 部分：

```python
CONFIG = {
    'nls_tts_voice': 'indah',    # 改为其他发音人
    'ai_model': 'gpt-3.5-turbo', # 改为gpt-4
    'vad_aggressiveness': 2,     # 改为1(宽容)或3(严格)
    ...
}
```

### 查看详细日志

```python
# 修改日志级别（在CONFIG中）
'log_level': 5,  # 最详细
```

### 后台运行

```bash
# 后台拨号
nohup ./call_nls.sh 85211111111 > call.log 2>&1 &

# 查看日志
tail -f call.log

# 查找进程
ps aux | grep sip_ai_nls_cli

# 终止
pkill -f sip_ai_nls_cli
```

---

## 🐛 故障排查

### 问题1: 提示"未设置 OPENAI_API_KEY"

```bash
export OPENAI_API_KEY='sk-proj-...'
```

### 问题2: 拨号失败

检查网络和SIP服务器：
```bash
nc -zv 147.139.205.88 5060
```

### 问题3: 无声音

检查TTS文件：
```bash
ls -lh temp_audio/tts_nls_*.wav
play temp_audio/tts_nls_*.wav
```

### 问题4: Token获取失败

可能是网络问题或阿里云服务问题，稍后重试。

---

## 💡 实用技巧

### 技巧1: 创建别名

```bash
# 添加到 ~/.bashrc
alias callnls='cd /home/henry/pjproject && ./call_nls.sh'

# 使用
callnls 85211111111
```

### 技巧2: 快速查看最新录音

```bash
alias lastcall='ls -t /home/henry/pjproject/recordings/call_nls_*.wav | head -1 | xargs play'

# 使用
lastcall
```

### 技巧3: 自动清理旧录音

```bash
# 保留最近10个录音
cd recordings
ls -t call_nls_*.wav | tail -n +11 | xargs rm -f
```

---

## 📋 快速命令参考

```bash
# 拨号
./call_nls.sh 85211111111

# 挂断
Ctrl+C

# 查看录音
ls -lh recordings/

# 播放录音
play recordings/call_nls_*.wav

# 查看临时文件
ls -lh temp_audio/

# 清理临时文件
rm -f temp_audio/*.wav

# 查看进程
ps aux | grep sip_ai_nls_cli

# 终止进程
pkill -f sip_ai_nls_cli
```

---

## 🎉 总结

**命令行版本特点**:

✅ **简单**: 一条命令就能拨号  
✅ **快速**: 无需打开浏览器  
✅ **直观**: 所有信息在控制台  
✅ **自动化**: 易于脚本集成  
✅ **轻量**: 无Web服务器开销  

**完美适合快速测试和自动化场景！** 🚀

---

## 🔗 相关文档

- Web版使用: `HOW_TO_USE_NLS.md`
- 完整文档: `NLS_INTEGRATION_README.md`
- 快速参考: `QUICK_REFERENCE_NLS.md`
- 测试指南: `TEST_NLS_INTEGRATION.md`

---

**现在就试试吧！** 📞

```bash
export OPENAI_API_KEY='your-key'
./call_nls.sh 85211111111
```

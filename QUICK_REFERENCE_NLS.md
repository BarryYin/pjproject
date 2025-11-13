# 🚀 NLS集成版快速参考

## 一键启动

```bash
export OPENAI_API_KEY='sk-proj-XCMmLidU_4KNH5bD...'
./start_nls_integrated.sh
```

访问: **http://localhost:8090**

---

## 核心文件

| 文件 | 说明 | 大小 |
|------|------|------|
| `sip_ai_nls_integrated.py` | 主程序 | 37KB (1101行) |
| `start_nls_integrated.sh` | 启动脚本 | 818B |
| `NLS_INTEGRATION_README.md` | 完整文档 | 9.2KB |
| `COMPARISON_ORIGINAL_VS_NLS.md` | 对比分析 | 7.0KB |
| `TEST_NLS_INTEGRATION.md` | 测试指南 | 12KB |

---

## 技术栈速览

```
┌─────────────────────────────────────┐
│  ASR: 阿里云NLS (WebSocket)         │
│  TTS: 阿里云NLS (WebSocket, 印尼语) │
│  AI:  OpenAI GPT-3.5-turbo         │
│  VAD: WebRTC                       │
│  SIP: PJSIP                        │
│  Web: HTTP + JavaScript            │
└─────────────────────────────────────┘
```

---

## 配置速查

### 阿里云NLS

```python
AKID    = 'LTAI5tGtuuJyivveR3UFARYs'
AKKEY   = 'aY32qhvLBpslrxwTUSO6tYlMscCitG'
AppKey  = 'dqAnq24vXe5lJUlq'
Voice   = 'indah'  # 印尼语女声
```

### SIP服务器

```python
Server  = '147.139.205.88:5060'
Caller  = '6281479242434'
Prefix  = '13462'
```

### 端口

```python
SIP Port  = 5060
Web Port  = 8090
```

---

## 命令速查

```bash
# 启动系统
./start_nls_integrated.sh

# 语法检查
python3 -m py_compile sip_ai_nls_integrated.py

# 测试TTS
python3 test_alibaba_tts.py

# 测试ASR
python3 test_alibaba_asr.py

# 查看日志（运行时）
# 直接在控制台查看

# 查看录音
ls -lh recordings/call_nls_*.wav

# 播放录音
play recordings/call_nls_20231113_203000.wav
```

---

## API速查

### 状态查询

```bash
curl http://localhost:8090/status
```

### 拨号

```bash
curl -X POST http://localhost:8090/call \
  -H "Content-Type: application/json" \
  -d '{"number":"85211111111"}'
```

### 挂断

```bash
curl -X POST http://localhost:8090/hangup
```

---

## 目录结构

```
/home/henry/pjproject/
├── sip_ai_nls_integrated.py      ← 主程序
├── start_nls_integrated.sh        ← 启动脚本
├── recordings/                    ← 录音文件
│   └── call_nls_*.wav
├── temp_audio/                    ← 临时音频
│   ├── speech_*.wav              ← VAD检测的语音
│   └── tts_nls_*.wav             ← TTS合成的音频
└── alibabacloud-nls-python-sdk/  ← NLS SDK
```

---

## 日志格式

```
[组件] 消息内容

组件代码:
  VAD  - 语音检测
  ASR  - 语音识别
  AI   - 对话引擎
  TTS  - 语音合成
  SIP  - 电话协议
  HTTP - Web服务
  状态 - 通话状态
  媒体 - 音频处理
  录音 - 录音管理
  播放 - 音频播放
  拨号 - 拨号操作
```

---

## 性能指标

| 指标 | 原版 | NLS版 | 提升 |
|------|------|-------|------|
| ASR延迟 | 1-2s | 0.3-0.8s | 60% ✅ |
| TTS延迟 | 1-2s | 0.5-1.0s | 50% ✅ |
| 总延迟 | 2-4s | 0.8-1.8s | 55% ✅ |

---

## 故障速查

| 错误 | 原因 | 解决 |
|------|------|------|
| Token获取失败 | AKID/AKKEY错误 | 检查配置 |
| ASR无结果 | 音频问题 | 检查录音 |
| TTS失败 | 网络问题 | 检查连接 |
| OpenAI错误 | Key未设置 | export KEY |
| VAD无检测 | 音量太小 | 调整参数 |
| 无声音 | 连接错误 | 检查音频链路 |

---

## 核心类速查

```python
WebRTCVADDetector      # VAD检测
  .process_audio()     # 处理音频
  .reset()             # 重置状态

NLSASREngine           # ASR引擎
  .get_token()         # 获取token
  .transcribe()        # 识别音频

NLSTTSEngine           # TTS引擎
  .get_token()         # 获取token
  .synthesize()        # 合成语音

DialogueEngine         # AI对话
  .get_response()      # 获取回复

AIConversationCallback # 主回调
  .on_state()          # 状态变化
  .on_media_state()    # 媒体状态
  .start_vad_recording() # 开始录音
  .vad_process_loop()  # VAD循环
  .process_speech()    # 处理语音
  .play_audio_response() # 播放回复
```

---

## 完整流程图

```
用户拨号
   ↓
通话接通 → 创建录音 → 启动VAD线程
   ↓
实时读取录音 (每100ms)
   ↓
VAD检测 → 检测到说话 → 收集音频帧
   ↓
静音判定 → 句子结束
   ↓
保存音频片段
   ↓
NLS ASR识别 (WebSocket)
   ↓
获取识别文本
   ↓
OpenAI生成回复
   ↓
NLS TTS合成 (WebSocket)
   ↓
播放到通话
   ↓
继续监听...
   ↓
用户挂断 → 停止VAD → 保存录音 → 结束
```

---

## Web界面操作

1. 访问 http://localhost:8090
2. 输入号码: `85211111111`
3. 点击 "📞 拨打电话"
4. 状态变为 "通话中"
5. 开始对话（印尼语）
6. 点击 "📴 挂断电话"

---

## 测试清单

- [ ] Token获取测试
- [ ] TTS基础测试
- [ ] ASR基础测试
- [ ] 语法检查
- [ ] 系统启动
- [ ] Web界面
- [ ] 拨号测试
- [ ] 对话测试
- [ ] 挂断测试
- [ ] 录音检查

---

## 关键数值

```python
# VAD参数
aggressiveness = 2        # 0-3，越高越严格
frame_duration = 30       # ms
silence_frames = 20       # 判定句子结束
min_speech_frames = 5     # 最少语音帧

# 音频参数
sample_rate = 8000        # Hz
channels = 1              # 单声道
sample_width = 2          # 16-bit

# 定时器
vad_read_interval = 0.1   # 100ms读取一次
status_update = 1.0       # 1秒更新状态
```

---

## 环境变量

```bash
# 必需
export OPENAI_API_KEY='sk-proj-...'

# 可选（已硬编码）
# export NLS_AKID='LTAI5...'
# export NLS_AKKEY='aY32...'
# export NLS_APPKEY='dqAn...'
```

---

## 端口占用检查

```bash
# 检查8090端口
lsof -i :8090

# 检查5060端口
lsof -i :5060
```

---

## 进程管理

```bash
# 查找进程
ps aux | grep sip_ai_nls_integrated

# 终止进程
pkill -f sip_ai_nls_integrated

# 后台运行
nohup ./start_nls_integrated.sh > nls.log 2>&1 &

# 查看日志
tail -f nls.log
```

---

## 磁盘空间管理

```bash
# 查看录音空间
du -sh recordings/

# 清理旧录音（保留最近7天）
find recordings/ -name "call_nls_*.wav" -mtime +7 -delete

# 清理临时文件
rm -f temp_audio/speech_*.wav
rm -f temp_audio/tts_nls_*.wav
```

---

## 常用检查命令

```bash
# 检查系统状态
curl -s http://localhost:8090/status | python3 -m json.tool

# 检查最新录音
ls -lht recordings/ | head -5

# 统计录音数量
ls -1 recordings/call_nls_*.wav | wc -l

# 检查进程
pgrep -fa python3.*sip_ai_nls

# 检查端口
netstat -tlnp | grep -E '8090|5060'
```

---

## 性能监控

```bash
# CPU使用
top -p $(pgrep -f sip_ai_nls_integrated)

# 内存使用
ps aux | grep sip_ai_nls_integrated | awk '{print $4"%"}'

# 网络连接
netstat -an | grep -E '8090|5060' | wc -l

# 磁盘IO
iotop -p $(pgrep -f sip_ai_nls_integrated)
```

---

## 调试技巧

```python
# 启用详细日志
CONFIG['log_level'] = 5  # 最详细

# 降低VAD灵敏度
CONFIG['vad_aggressiveness'] = 1  # 更宽容

# 增加静音帧数
CONFIG['vad_silence_frames'] = 30  # 更长静音

# 调试VAD
在 vad_process_loop() 中添加:
print(f"[DEBUG] 读取数据: {len(new_data)}字节")
```

---

## 快速修改

### 修改TTS发音人

```python
CONFIG['nls_tts_voice'] = 'xiaoyun'  # 中文
CONFIG['nls_tts_voice'] = 'indah'    # 印尼语
```

### 修改AI模型

```python
CONFIG['ai_model'] = 'gpt-4'         # 更强大
CONFIG['ai_model'] = 'gpt-3.5-turbo' # 更快更便宜
```

### 修改端口

```python
CONFIG['api_port'] = 8091  # 改变Web端口
```

---

## 文档链接

- 完整文档: `NLS_INTEGRATION_README.md`
- 对比分析: `COMPARISON_ORIGINAL_VS_NLS.md`
- 测试指南: `TEST_NLS_INTEGRATION.md`
- 原版文档: `AI_CONVERSATION_SYSTEM_README.md`

---

## 获取帮助

1. 查看日志输出
2. 检查 `TEST_NLS_INTEGRATION.md` 故障排查部分
3. 参考 `NLS_INTEGRATION_README.md` 技术细节
4. 对比原版: `COMPARISON_ORIGINAL_VS_NLS.md`

---

## 版本信息

- 创建日期: 2023-11-13
- Python版本: 3.11+
- PJSIP版本: 2.x
- NLS SDK: 最新版

---

**保存此文档供快速查阅！** 📌

# 🎯 如何使用 NLS集成版 - 超简单教程

## 📋 使用前准备

### 1️⃣ 确认环境

```bash
# 检查Python版本（需要3.11+）
python3 --version

# 检查目录
cd /home/henry/pjproject
ls -l sip_ai_nls_integrated.py
```

### 2️⃣ 设置API Key

```bash
# 设置OpenAI API Key（必需）
export OPENAI_API_KEY='sk-proj-XCMmLidU_4KNH5bD...'

# 验证是否设置成功
echo $OPENAI_API_KEY
```

**注意**: 阿里云NLS的配置已经内置在代码中，无需额外设置！

---

## 🚀 三种使用方法

### 方法1: 使用启动脚本（推荐）⭐

```bash
cd /home/henry/pjproject

# 设置OpenAI Key
export OPENAI_API_KEY='your-key-here'

# 一键启动
./start_nls_integrated.sh
```

**看到这个界面说明启动成功**:
```
======================================================================
  AI对话系统 - 阿里云NLS WebSocket完整集成版
======================================================================
  ASR: 阿里云NLS实时识别
  TTS: 阿里云NLS语音合成 (发音人: indah)
  AI:  OpenAI gpt-3.5-turbo
  VAD: WebRTC (激进度: 2)
======================================================================

[VAD] WebRTC VAD初始化 (激进度:2, 帧长:30ms)
[ASR] 初始化阿里云NLS ASR引擎...
[TTS] 初始化阿里云NLS TTS引擎 (发音人:indah)...
[AI] 初始化 gpt-3.5-turbo 对话引擎

[SIP] 传输启动: UDP 端口 5060
[SIP] 账户创建: sip:6281479242434@147.139.205.88

[HTTP] Web界面: http://localhost:8090

✓ 系统已启动，可以通过Web界面拨打电话
  按 Ctrl+C 退出
```

---

### 方法2: 直接运行Python脚本

```bash
cd /home/henry/pjproject

# 设置环境变量
export OPENAI_API_KEY='your-key-here'

# 直接运行
python3 sip_ai_nls_integrated.py
```

---

### 方法3: 后台运行（生产环境）

```bash
cd /home/henry/pjproject

# 设置环境变量
export OPENAI_API_KEY='your-key-here'

# 后台运行并记录日志
nohup python3 sip_ai_nls_integrated.py > nls_system.log 2>&1 &

# 查看进程ID
echo $!

# 查看日志
tail -f nls_system.log

# 停止系统
pkill -f sip_ai_nls_integrated
```

---

## 🎮 使用Web界面拨打电话

### 步骤1: 打开浏览器

访问: **http://localhost:8090**

你会看到这样的界面：

```
┌─────────────────────────────────────┐
│   🤖 AI对话系统                      │
│   阿里云NLS WebSocket完整集成版       │
├─────────────────────────────────────┤
│                                     │
│  技术栈:                             │
│  • ASR: 阿里云NLS实时识别 (WebSocket)│
│  • TTS: 阿里云NLS语音合成 (印尼语)   │
│  • AI: OpenAI GPT-3.5-turbo        │
│  • VAD: WebRTC实时检测              │
│                                     │
│  ┌───────────────────────────────┐  │
│  │ 等待拨号                       │  │
│  └───────────────────────────────┘  │
│                                     │
│  ┌───────────────────────────────┐  │
│  │ 输入电话号码 (例: 85211111111) │  │
│  └───────────────────────────────┘  │
│                                     │
│  [ 📞 拨打电话 ]                    │
│  [ 📴 挂断电话 ] (灰色/禁用)        │
│                                     │
└─────────────────────────────────────┘
```

### 步骤2: 输入电话号码

在输入框中输入目标号码，例如: `85211111111`

**注意**: 系统会自动加前缀 `13462`，实际拨打: `1346285211111111`

### 步骤3: 点击"拨打电话"

点击绿色的"📞 拨打电话"按钮

**界面变化**:
```
状态: 正在呼叫: sip:1346285211111111@147.139.205.88
```

**控制台输出**:
```
[拨号] sip:1346285211111111@147.139.205.88
[状态] CALLING - 183
[状态] EARLY - 183
```

### 步骤4: 等待接通

接通后，界面显示：
```
状态: 通话中: sip:1346285211111111@147.139.205.88 (AI对话已激活)
```

**控制台输出**:
```
[状态] CONFIRMED - 200
[状态] >>> 通话已接通，启动AI对话系统
[录音] 开始录音: recordings/call_nls_20231113_204530.wav
[VAD] 处理循环启动
[媒体] 双向音频通道已激活
```

### 步骤5: 开始对话

现在可以与AI进行印尼语对话了！

**对话流程示例**:

1. **对方说话**: "Halo, apa kabar?"
   
   **控制台显示**:
   ```
   [VAD] >>> 检测到说话
   [VAD] <<< 句子结束 (45帧)
   [处理] 保存语音: speech_20231113_204535_123456.wav (8640字节)
   [ASR] 开始识别: speech_20231113_204535_123456.wav
   [ASR] 正在获取token...
   [ASR] Token获取成功: xxxx...
   [ASR] ✓ 识别成功: 'Halo, apa kabar?' (0.6s)
   ```

2. **AI思考**: 
   ```
   [AI] 用户: 'Halo, apa kabar?'
   [AI] 回复: 'Halo! Saya baik, terima kasih. Bagaimana dengan Anda?' (1.0s)
   ```

3. **TTS合成**:
   ```
   [TTS] 开始合成: 'Halo! Saya baik, terima kasih...'
   [TTS] 正在获取token...
   [TTS] Token获取成功: xxxx...
   [TTS] ✓ 合成成功: 272442字节 (0.8s)
   ```

4. **播放回复**:
   ```
   [播放] 开始播放: tts_nls_20231113_204537_789012.wav
   [播放] 播放完成
   ```

5. **继续对话**: 系统会持续监听对方说话...

### 步骤6: 挂断电话

对话结束后，点击红色的"📴 挂断电话"按钮

**控制台输出**:
```
[状态] DISCONNECTED - 200
[状态] >>> 通话已结束
[VAD] 处理循环已停止
[录音] 已停止，文件: recordings/call_nls_20231113_204530.wav
```

**界面恢复**:
```
状态: 等待拨号
```

---

## 🔍 查看录音文件

```bash
# 查看所有录音
ls -lh recordings/call_nls_*.wav

# 查看最新录音
ls -lht recordings/call_nls_*.wav | head -1

# 播放录音（如果有音频播放器）
play recordings/call_nls_20231113_204530.wav

# 或使用ffplay
ffplay recordings/call_nls_20231113_204530.wav
```

---

## 🔧 常见问题

### Q1: 提示"未设置 OPENAI_API_KEY"

**解决**:
```bash
export OPENAI_API_KEY='sk-proj-your-key-here'
```

### Q2: 提示"未找到阿里云NLS SDK"

**解决**:
```bash
# 检查SDK目录是否存在
ls -ld alibabacloud-nls-python-sdk

# 如果不存在，需要先下载/克隆SDK
```

### Q3: 端口8090已被占用

**解决**:
```bash
# 查看占用进程
lsof -i :8090

# 终止占用进程
kill -9 <PID>

# 或者修改配置文件中的端口
# 编辑 sip_ai_nls_integrated.py
# 修改: CONFIG['api_port'] = 8091
```

### Q4: 无法拨号

**可能原因**:
1. SIP服务器不可达
2. 账号配置错误
3. 网络问题

**检查**:
```bash
# 测试SIP服务器连接
nc -zv 147.139.205.88 5060

# 查看控制台错误日志
```

### Q5: 对方听不到AI回复

**可能原因**:
1. TTS合成失败
2. 音频播放失败
3. 网络问题

**检查**:
```bash
# 查看临时TTS文件
ls -lh temp_audio/tts_nls_*.wav

# 播放TTS文件确认内容
play temp_audio/tts_nls_*.wav
```

### Q6: ASR识别不准确

**解决**:
1. 检查对方音量是否太小
2. 检查网络连接是否稳定
3. 查看录音文件质量
4. 考虑调整VAD参数

```python
# 降低VAD灵敏度（在代码中修改）
CONFIG['vad_aggressiveness'] = 1  # 改为1（更宽容）
```

---

## 📊 监控系统状态

### 使用curl查询状态

```bash
# 查询系统状态
curl http://localhost:8090/status

# 输出示例（空闲状态）
{"status": "idle", "number": ""}

# 输出示例（通话中）
{"status": "connected", "number": "sip:1346285211111111@147.139.205.88"}
```

### 实时查看日志

```bash
# 如果是前台运行，直接看控制台

# 如果是后台运行
tail -f nls_system.log
```

### 监控性能

```bash
# CPU使用率
top -p $(pgrep -f sip_ai_nls_integrated)

# 内存使用
ps aux | grep sip_ai_nls_integrated

# 网络连接
netstat -an | grep -E '8090|5060'
```

---

## 🎯 使用技巧

### 技巧1: 测试识别准确度

```bash
# 准备测试音频
# 确保音频格式: WAV, 8000Hz, 单声道, 16-bit

# 手动测试ASR
python3 test_alibaba_asr.py

# 手动测试TTS
python3 test_alibaba_tts.py
```

### 技巧2: 调整对话风格

编辑 `sip_ai_nls_integrated.py`，找到 `DialogueEngine` 类：

```python
class DialogueEngine:
    def __init__(self):
        self.system_prompt = f"""You are a helpful AI assistant speaking in Indonesian.
Keep responses concise and natural (1-2 sentences).
You are having a phone conversation, so be conversational and friendly."""
```

可以修改 `system_prompt` 来调整AI的对话风格。

### 技巧3: 切换语言

```python
# 修改TTS发音人（在CONFIG中）
CONFIG['nls_tts_voice'] = 'xiaoyun'  # 中文女声
CONFIG['nls_tts_voice'] = 'indah'    # 印尼语女声（默认）

# 修改AI语言
CONFIG['ai_language'] = 'zh'  # 中文
CONFIG['ai_language'] = 'id'  # 印尼语（默认）
```

### 技巧4: 清理临时文件

```bash
# 定期清理临时语音文件
rm -f temp_audio/speech_*.wav
rm -f temp_audio/tts_nls_*.wav

# 清理旧录音（保留最近7天）
find recordings/ -name "call_nls_*.wav" -mtime +7 -delete
```

---

## 🎬 完整使用流程示例

```bash
# 1. 准备环境
cd /home/henry/pjproject
export OPENAI_API_KEY='sk-proj-...'

# 2. 启动系统
./start_nls_integrated.sh

# 3. 打开浏览器
# 访问 http://localhost:8090

# 4. 拨打电话
# 输入号码: 85211111111
# 点击"拨打电话"

# 5. 等待接通
# 看到"通话中"状态

# 6. 开始对话
# 对方说话 → AI自动识别回复

# 7. 挂断电话
# 点击"挂断电话"

# 8. 查看录音
ls -lh recordings/call_nls_*.wav

# 9. 停止系统（前台运行）
# 按 Ctrl+C

# 10. 停止系统（后台运行）
pkill -f sip_ai_nls_integrated
```

---

## 📱 使用场景示例

### 场景1: 客户服务

```
客户: "Halo, saya ingin tahu tentang produk Anda"
AI: "Halo! Dengan senang hati saya akan membantu Anda. Produk apa yang ingin Anda ketahui?"
客户: "Tentang harga"
AI: "Baik, untuk informasi harga detail, saya akan menghubungkan Anda dengan tim sales kami."
```

### 场景2: 预约确认

```
客户: "Saya mau konfirmasi appointment besok"
AI: "Baik, boleh saya tahu nama Anda?"
客户: "John Smith"
AI: "Terima kasih Pak John. Appointment Anda besok jam 10 pagi sudah terkonfirmasi."
```

### 场景3: 信息查询

```
客户: "Jam berapa toko buka?"
AI: "Toko kami buka setiap hari dari jam 9 pagi sampai 9 malam."
客户: "Terima kasih"
AI: "Sama-sama! Ada yang bisa saya bantu lagi?"
```

---

## 🎓 进阶使用

### 1. 添加自定义命令

在 `DialogueEngine` 中可以添加命令识别逻辑：

```python
def get_response(self, user_input):
    # 添加命令识别
    if "transfer" in user_input.lower():
        return "Baik, saya akan transfer ke operator."
    
    if "goodbye" in user_input.lower():
        return "Terima kasih sudah menghubungi kami. Selamat tinggal!"
    
    # 正常对话
    return self._call_openai(user_input)
```

### 2. 记录对话历史到数据库

```python
def process_speech(self, audio_data):
    text = self.asr.transcribe(audio_file)
    response = self.dialogue.get_response(text)
    
    # 保存到数据库
    self.save_conversation(
        timestamp=datetime.now(),
        user_input=text,
        ai_response=response,
        call_id=self.record_file
    )
```

### 3. 添加情感分析

```python
def analyze_sentiment(self, text):
    # 使用OpenAI分析情感
    prompt = f"Analyze sentiment of: {text}"
    # ...
    return sentiment_score
```

---

## 🆘 获取帮助

如果遇到问题：

1. **查看日志**: 控制台会显示详细的错误信息
2. **参考测试文档**: `TEST_NLS_INTEGRATION.md`
3. **查看完整文档**: `NLS_INTEGRATION_README.md`
4. **对比原版**: `COMPARISON_ORIGINAL_VS_NLS.md`

---

## ✅ 使用检查清单

- [ ] 已设置 OPENAI_API_KEY
- [ ] alibabacloud-nls-python-sdk 目录存在
- [ ] 系统启动无错误
- [ ] Web界面可访问
- [ ] 可以成功拨号
- [ ] VAD检测工作正常
- [ ] ASR识别准确
- [ ] TTS播放清晰
- [ ] 录音文件已保存

---

**现在你已经完全掌握如何使用NLS集成版了！** 🎉

开始你的第一次AI电话对话吧！📞

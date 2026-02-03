# NLS集成版测试指南

## ✅ 测试前检查清单

### 1. 环境准备

- [ ] Python 3已安装
- [ ] PJSIP库已编译
- [ ] OpenAI API Key已设置
- [ ] 网络连接正常

```bash
# 检查Python
python3 --version

# 检查PJSIP
python3 -c "import pjsua as pj; print('PJSIP OK')"

# 检查OpenAI Key
echo $OPENAI_API_KEY

# 检查网络
ping -c 3 nls-gateway.cn-shanghai.aliyuncs.com
```

### 2. 依赖检查

- [ ] pjsua模块可用
- [ ] webrtcvad已安装
- [ ] openai已安装
- [ ] 阿里云NLS SDK可用

```bash
# 检查依赖
python3 << 'EOF'
import sys
sys.path.insert(0, 'alibabacloud-nls-python-sdk')

try:
    import pjsua
    print("✓ pjsua")
except:
    print("✗ pjsua - 需要编译PJSIP")

try:
    import webrtcvad
    print("✓ webrtcvad")
except:
    print("✗ webrtcvad - pip install webrtcvad")

try:
    import openai
    print("✓ openai")
except:
    print("✗ openai - pip install openai")

try:
    import nls
    print("✓ nls SDK")
except:
    print("✗ nls SDK - 检查alibabacloud-nls-python-sdk目录")
EOF
```

### 3. 配置检查

- [ ] 阿里云AKID/AKKEY正确
- [ ] AppKey正确
- [ ] SIP服务器可达
- [ ] 录音目录存在

```bash
# 检查目录
ls -ld recordings/ temp_audio/ audio_files/

# 测试SIP服务器连接
nc -zv 147.139.205.88 5060
```

## 🧪 单元测试

### 测试1: NLS Token获取

```bash
python3 << 'EOF'
import sys
sys.path.insert(0, 'alibabacloud-nls-python-sdk')
from nls.token import getToken

AKID = os.getenv('ALI_NLS_AKID', '')
AKKEY = os.getenv('ALI_NLS_AKKEY', '')

try:
    token = getToken(AKID, AKKEY)
    print(f"✓ Token获取成功: {token[:30]}...")
except Exception as e:
    print(f"✗ Token获取失败: {e}")
EOF
```

**预期结果**: 看到token字符串

---

### 测试2: NLS TTS基础测试

```bash
python3 test_alibaba_tts.py
```

**预期结果**:
- 看到"合成完成"消息
- 生成 `test_alibaba_tts_output.wav` 文件
- 文件大小 > 100KB

---

### 测试3: NLS ASR基础测试

```bash
python3 test_alibaba_asr.py
```

**预期结果**:
- 看到识别结果
- 识别准确率 > 90%

---

### 测试4: 语法检查

```bash
python3 -m py_compile sip_ai_nls_integrated.py
echo "✓ 语法检查通过"
```

**预期结果**: 无错误输出

---

## 🚀 集成测试

### 测试5: 系统启动测试

```bash
# 设置API Key
export OPENAI_API_KEY='sk-proj-XCMmLidU_4KNH5bD...'

# 启动系统（Ctrl+C退出）
./start_nls_integrated.sh
```

**预期结果**:
```
======================================================================
  AI对话系统 - 阿里云NLS WebSocket完整集成版
======================================================================
  ASR: 阿里云NLS实时识别
  TTS: 阿里云NLS语音合成 (发音人: indah)
  AI:  OpenAI gpt-3.5-turbo
  VAD: WebRTC (激进度: 2)
======================================================================

✓ OpenAI API Key 已设置

✓ 阿里云NLS SDK 已就绪

正在启动系统...

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

**检查项**:
- [ ] 无错误消息
- [ ] VAD初始化成功
- [ ] ASR/TTS引擎初始化
- [ ] SIP账户创建
- [ ] HTTP服务器启动

---

### 测试6: Web界面测试

1. **访问界面**
   ```bash
   # 在浏览器打开
   http://localhost:8090
   ```

2. **检查内容**
   - [ ] 页面正常显示
   - [ ] 看到"阿里云NLS WebSocket完整集成版"标题
   - [ ] 技术栈信息显示
   - [ ] 电话号码输入框
   - [ ] 拨打/挂断按钮

3. **测试状态API**
   ```bash
   curl http://localhost:8090/status
   ```
   
   **预期结果**:
   ```json
   {"status": "idle", "number": ""}
   ```

---

### 测试7: 拨号测试

1. **在Web界面输入测试号码**: `85211111111`
2. **点击"拨打电话"**
3. **观察控制台输出**

**预期日志流程**:
```
[拨号] sip:1346285211111111@147.139.205.88

[状态] CALLING - 183

[状态] CONFIRMED - 200
[状态] >>> 通话已接通，启动AI对话系统
[录音] 开始录音: recordings/call_nls_20231113_203000.wav
[VAD] 处理循环启动

[媒体] 双向音频通道已激活
```

**检查项**:
- [ ] 拨号成功
- [ ] 状态变为"通话中"
- [ ] VAD循环启动
- [ ] 录音文件创建

---

### 测试8: 对话测试

**当对方说话时观察**:

```
[VAD] >>> 检测到说话
[VAD] <<< 句子结束 (45帧)
[处理] 保存语音: speech_20231113_203005_123456.wav (8640字节)
[ASR] 开始识别: speech_20231113_203005_123456.wav
[ASR] 正在获取token...
[ASR] Token获取成功: xxxx...
[ASR] ✓ 识别成功: 'Halo, apa kabar?' (0.6s)
[AI] 用户: 'Halo, apa kabar?'
[AI] 回复: 'Halo! Saya baik, terima kasih.' (1.0s)
[TTS] 开始合成: 'Halo! Saya baik, terima kasih.'
[TTS] 正在获取token...
[TTS] Token获取成功: xxxx...
[TTS] ✓ 合成成功: 272442字节 (0.8s)
[播放] 开始播放: tts_nls_20231113_203007_789012.wav
[播放] 播放完成
```

**检查项**:
- [ ] VAD检测到说话
- [ ] ASR识别成功
- [ ] AI生成回复
- [ ] TTS合成成功
- [ ] 音频播放到通话

**测量延迟**:
- VAD检测: ~0.5s
- ASR识别: ~0.6s
- AI回复: ~1.0s
- TTS合成: ~0.8s
- **总延迟**: ~2.9s ✅

---

### 测试9: 挂断测试

1. **点击"挂断电话"按钮**
2. **观察控制台**

**预期输出**:
```
[状态] DISCONNECTED - 200
[状态] >>> 通话已结束
[VAD] 处理循环已停止
[录音] 已停止，文件: recordings/call_nls_20231113_203000.wav
```

**检查项**:
- [ ] VAD循环停止
- [ ] 录音文件保存
- [ ] 状态恢复为"等待拨号"

---

### 测试10: 录音文件检查

```bash
# 查看最新录音
ls -lh recordings/call_nls_*.wav | tail -1

# 播放录音（如果有音频播放器）
# play recordings/call_nls_20231113_203000.wav

# 查看临时文件
ls -lh temp_audio/speech_*.wav | tail -5
ls -lh temp_audio/tts_nls_*.wav | tail -5
```

**检查项**:
- [ ] 录音文件存在
- [ ] 文件大小合理（通话时长 × 16KB/s）
- [ ] 临时语音文件已生成
- [ ] TTS文件已生成

---

## 🐛 故障排查

### 问题1: Token获取失败

**症状**: `[ASR] Token获取失败` 或 `[TTS] Token获取失败`

**原因**:
- AKID/AKKEY错误
- 网络连接问题
- 阿里云服务异常

**解决**:
```bash
# 测试Token API
curl "https://nls-meta.cn-shanghai.aliyuncs.com/token" \
  -d "AccessKeyId=$(echo $ALI_NLS_AKID)" \
  -d "AccessKeySecret=$(echo $ALI_NLS_AKKEY)"
```

---

### 问题2: ASR识别无结果

**症状**: `[ASR] ✗ 识别失败或无结果`

**原因**:
- 音频格式不对
- 音频太短
- 网络超时

**解决**:
1. 检查音频文件: `file temp_audio/speech_*.wav`
2. 播放音频确认内容
3. 增加识别超时时间

---

### 问题3: TTS合成失败

**症状**: `[TTS] ✗ 合成失败`

**原因**:
- 文本为空
- Token过期
- 网络问题

**解决**:
1. 检查AI回复文本
2. 重新获取Token
3. 检查网络连接

---

### 问题4: OpenAI API错误

**症状**: `[AI] 错误: ...`

**原因**:
- API Key未设置或错误
- 配额用完
- 网络问题

**解决**:
```bash
# 测试OpenAI API
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

---

### 问题5: VAD不检测说话

**症状**: 没有 `[VAD] >>> 检测到说话`

**原因**:
- 录音文件没有数据
- VAD参数太激进
- 音量太小

**解决**:
1. 检查录音文件大小是否增长
2. 降低VAD激进度（改为1）
3. 增加音量

---

### 问题6: 播放无声音

**症状**: `[播放] 开始播放` 但对方听不到

**原因**:
- 音频连接错误
- 音频文件为空
- PJSIP配置问题

**解决**:
1. 检查TTS文件大小
2. 本地播放TTS文件测试
3. 检查conf_connect调用

---

## 📊 性能测试

### 测试11: 延迟测试

进行10次对话，记录每次延迟：

| 轮次 | VAD | ASR | AI | TTS | 总计 |
|------|-----|-----|----|----|------|
| 1    |     |     |    |    |      |
| 2    |     |     |    |    |      |
| ...  |     |     |    |    |      |
| 平均 |     |     |    |    |      |

**目标**: 总延迟 < 2秒

---

### 测试12: 识别准确率测试

准备10句印尼语测试语句：

| 序号 | 原文 | 识别结果 | 准确 |
|------|------|---------|------|
| 1    | Halo, apa kabar? | | |
| 2    | Selamat pagi | | |
| ...  | | | |

**目标**: 准确率 > 95%

---

### 测试13: TTS质量测试

评估TTS输出质量（主观）：

- [ ] 发音清晰
- [ ] 语调自然
- [ ] 音量适中
- [ ] 无杂音
- [ ] 印尼语地道

**目标**: 所有项通过

---

## ✅ 测试通过标准

### 基础功能

- [x] 系统启动无错误
- [x] Web界面可访问
- [x] 拨号成功
- [x] 通话接通
- [x] VAD检测工作
- [x] ASR识别成功
- [x] AI生成回复
- [x] TTS合成成功
- [x] 音频播放正常
- [x] 挂断正常
- [x] 录音保存

### 性能指标

- [ ] 端到端延迟 < 2秒
- [ ] ASR准确率 > 95%
- [ ] TTS质量评分 > 4/5
- [ ] 系统稳定运行 > 30分钟

### 用户体验

- [ ] 对话流畅自然
- [ ] 响应及时
- [ ] 印尼语质量好
- [ ] Web界面友好

---

## 🎉 测试完成

如果所有测试通过，恭喜！🎊

这个NLS集成版已经可以投入使用了！

**下一步**:
1. 在生产环境部署
2. 监控性能指标
3. 收集用户反馈
4. 持续优化

---

## 📝 测试记录模板

```
测试日期: ____________________
测试人员: ____________________
环境信息: ____________________

基础测试:
□ Token获取    □ TTS测试    □ ASR测试    □ 语法检查
□ 系统启动    □ Web界面    □ 拨号测试
□ 对话测试    □ 挂断测试    □ 录音检查

性能测试:
平均延迟: _______ 秒
ASR准确率: _______ %
TTS质量: _______ /5

问题记录:
1. _________________________________
2. _________________________________
3. _________________________________

总体评价:
□ 优秀    □ 良好    □ 合格    □ 需改进

备注:
_____________________________________
_____________________________________
```

---

**祝测试顺利！** 🚀

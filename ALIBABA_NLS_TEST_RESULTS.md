# 阿里云智能语音服务 (NLS) 测试结果

## 测试配置

- **AccessKey ID**: LTAI5tGtuuJyivveR3UFARYs
- **AccessKey Secret**: aY32qhvLBpslrxwTUSO6tYlMscCitG
- **AppKey**: dqAnq24vXe5lJUlq
- **SDK**: alibabacloud-nls-python-sdk

## 测试结果

### ✓ TTS (语音合成) 测试通过

**测试脚本**: `test_alibaba_tts.py`

**测试内容**:
- 文本: "Selamat pagi RISSA S.E pinjaman Anda sebesar 970200.0 akan segera jatuh tempo."
- 发音人: **indah** (印尼语女声)
- 音频格式: WAV
- 采样率: 16000 Hz
- 语言: 印尼语

**测试结果**:
- ✅ Token获取成功
- ✅ TTS连接成功
- ✅ 语音合成完成
- ✅ 音频文件生成: `test_alibaba_tts_output.wav` (~266KB)
- ✅ 印尼语发音正确

### ✓ ASR (语音识别) 测试通过

**测试脚本**: `test_alibaba_asr.py`

**测试内容**:
- 音频文件: SDK自带的测试音频 (test1.pcm, 183KB)
- 音频格式: PCM
- 采样率: 16000 Hz
- 功能: 一句话识别

**测试结果**:
- ✅ Token获取成功
- ✅ ASR连接成功
- ✅ 实时中间结果返回正常
- ✅ 最终识别结果: "一二三四五六七八九十"
- ✅ 识别准确度: 100%

## SDK使用要点

### 1. Token获取
```python
from nls.token import getToken

token = getToken(AKID, AKKEY)
```

### 2. TTS 使用
```python
import nls

tts = nls.NlsSpeechSynthesizer(
    token=token,
    appkey=APPKEY,
    long_tts=False,
    on_data=on_data_callback,
    on_completed=on_completed_callback,
    on_error=on_error_callback,
    on_close=on_close_callback
)

tts.start(
    text="要合成的文本",
    voice="indah",  # 印尼语女声，其他选项: xiaoyun(中文), harry(英文)等
    aformat="wav",
    sample_rate=16000
)
```

### 3. ASR 使用
```python
import nls

sr = nls.NlsSpeechRecognizer(
    token=token,
    appkey=APPKEY,
    on_start=on_start_callback,
    on_result_changed=on_result_changed_callback,
    on_completed=on_completed_callback,
    on_error=on_error_callback,
    on_close=on_close_callback
)

sr.start(
    aformat="pcm",
    sample_rate=16000,
    enable_intermediate_result=True,
    enable_punctuation_prediction=True,
    enable_inverse_text_normalization=True
)

# 发送音频数据
sr.send_audio(audio_data)

# 结束识别
sr.stop()
```

## 支持的语言和发音人

### TTS 常用发音人：
- **中文**: xiaoyun(标准女声), xiaogang(标准男声), ruoxi(温柔女声)
- **印尼语**: **indah**(印尼语女声) ⭐
- **英语**: harry(英音男声), abby(美音女声), wendy(英音女声)
- **马来语**: farah(马来语女声)
- **日语**: tomoka(日语女声), tomoya(日语男声)
- **粤语**: shanshan(粤语女声), jiajia(粤语女声)
- **更多**: 支持韩语、越南语、泰语、俄语、西班牙语、意大利语、法语、德语等

完整发音人列表请参考: https://help.aliyun.com/zh/isi/developer-reference/sdk-reference-1

## 注意事项

1. **Token有效期**: Token有24小时有效期，建议在应用中缓存token并在过期前刷新
2. **音频格式**: 
   - TTS支持: PCM, WAV, MP3
   - ASR支持: PCM, OPU, OPUS
3. **采样率**: 建议使用16000 Hz
4. **错误处理**: SDK通过异常来报错，没有抛异常即为成功
5. **回调函数**: 所有回调都是异步的，需要妥善处理线程安全
6. **印尼语TTS**: 使用 `voice="indah"` 参数，仅支持纯印尼语文本

## 测试命令

```bash
# 测试TTS
python3 test_alibaba_tts.py

# 测试ASR
python3 test_alibaba_asr.py

# 播放生成的音频
ffplay test_alibaba_tts_output.wav
```

## 结论

✅ 阿里云NLS服务的ASR和TTS功能均测试通过，配置正确，可以正常使用。

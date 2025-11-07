# 音频文件准备指南

## 音频文件位置

所有音频文件应放在：
```
/home/henry/pjproject/audio_files/
```

## 推荐音频格式

### 标准规格
```
格式: WAV (PCM)
采样率: 8000 Hz
声道: 单声道 (Mono)
位深度: 16-bit
编码: PCM s16le
```

### 为什么使用这些参数？

- **8000 Hz**: 电话语音标准采样率，足够清晰且节省带宽
- **单声道**: 电话是单声道，使用立体声浪费空间
- **16-bit**: 平衡音质和文件大小
- **PCM**: 未压缩，兼容性最好

## 音频转换工具

### 使用 FFmpeg 转换

#### 单个文件转换
```bash
# MP3 转 WAV
ffmpeg -i input.mp3 -ar 8000 -ac 1 -acodec pcm_s16le output.wav

# M4A 转 WAV
ffmpeg -i input.m4a -ar 8000 -ac 1 -acodec pcm_s16le output.wav

# MP4 音频提取
ffmpeg -i video.mp4 -ar 8000 -ac 1 -acodec pcm_s16le audio.wav

# OGG 转 WAV
ffmpeg -i input.ogg -ar 8000 -ac 1 -acodec pcm_s16le output.wav
```

#### 批量转换
```bash
# 转换当前目录所有MP3文件
for file in *.mp3; do
    ffmpeg -i "$file" -ar 8000 -ac 1 -acodec pcm_s16le "${file%.mp3}.wav"
done

# 转换所有M4A文件
for file in *.m4a; do
    ffmpeg -i "$file" -ar 8000 -ac 1 -acodec pcm_s16le "${file%.m4a}.wav"
done
```

#### 调整音量
```bash
# 增大音量 (2倍)
ffmpeg -i input.wav -ar 8000 -ac 1 -filter:a "volume=2.0" output.wav

# 降低音量 (0.5倍)
ffmpeg -i input.wav -ar 8000 -ac 1 -filter:a "volume=0.5" output.wav

# 自动标准化音量
ffmpeg -i input.wav -ar 8000 -ac 1 -filter:a loudnorm output.wav
```

#### 剪辑音频
```bash
# 截取前10秒
ffmpeg -i input.wav -t 10 -ar 8000 -ac 1 -acodec pcm_s16le output.wav

# 截取3-8秒片段
ffmpeg -i input.wav -ss 3 -t 5 -ar 8000 -ac 1 -acodec pcm_s16le output.wav

# 去除前后静音
ffmpeg -i input.wav -af silenceremove=1:0:-50dB -ar 8000 -ac 1 output.wav
```

### 使用 SoX 转换

```bash
# 安装 SoX
sudo apt-get install sox

# 基本转换
sox input.mp3 -r 8000 -c 1 -b 16 output.wav

# 添加淡入淡出效果
sox input.mp3 -r 8000 -c 1 output.wav fade 0.5 0 0.5

# 改变速度（不改变音调）
sox input.mp3 -r 8000 -c 1 output.wav tempo 1.2  # 加快20%
sox input.mp3 -r 8000 -c 1 output.wav tempo 0.8  # 减慢20%
```

## 建议的音频文件列表

### 基础IVR系统
```
audio_files/
├── welcome.wav          # 欢迎语 "您好，欢迎致电..."
├── main_menu.wav        # 主菜单 "请按1查询，按2服务..."
├── please_wait.wav      # 等待提示 "请稍候..."
├── thank_you.wav        # 感谢语 "感谢您的来电"
├── goodbye.wav          # 再见 "再见"
└── error.wav            # 错误提示 "输入有误，请重试"
```

### 完整客服系统
```
audio_files/
├── welcome.wav
├── main_menu.wav
├── submenu_1.wav
├── submenu_2.wav
├── option_1_info.wav
├── option_2_info.wav
├── option_3_info.wav
├── please_hold.wav
├── transferring.wav
├── voicemail_prompt.wav
├── recording_beep.wav
├── thank_you.wav
├── goodbye.wav
├── invalid_input.wav
├── timeout_warning.wav
└── service_unavailable.wav
```

### 多语言支持
```
audio_files/
├── en/
│   ├── welcome.wav
│   ├── menu.wav
│   └── goodbye.wav
├── id/  # 印度尼西亚语
│   ├── welcome.wav
│   ├── menu.wav
│   └── goodbye.wav
└── zh/  # 中文
    ├── welcome.wav
    ├── menu.wav
    └── goodbye.wav
```

## 在线TTS生成音频

### 使用Google TTS (gTTS)
```bash
# 安装
pip3 install gtts

# Python脚本生成
from gtts import gTTS
import os

texts = {
    'welcome': '您好，欢迎致电客服中心',
    'menu': '请按1查询订单，按2联系客服，按3留言',
    'goodbye': '感谢您的来电，再见'
}

for name, text in texts.items():
    tts = gTTS(text=text, lang='zh-cn')
    tts.save(f'{name}_raw.mp3')
    
    # 转换为电话格式
    os.system(f'ffmpeg -i {name}_raw.mp3 -ar 8000 -ac 1 -acodec pcm_s16le audio_files/{name}.wav')
    os.remove(f'{name}_raw.mp3')
```

### 使用Azure TTS (更自然)
```python
import azure.cognitiveservices.speech as speechsdk
import os

speech_key = "YOUR_AZURE_KEY"
service_region = "eastasia"

speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
speech_config.speech_synthesis_voice_name = "zh-CN-XiaoxiaoNeural"

def generate_audio(text, filename):
    audio_config = speechsdk.audio.AudioOutputConfig(filename=filename)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    synthesizer.speak_text(text)
    
    # 转换格式
    os.system(f'ffmpeg -i {filename} -ar 8000 -ac 1 -acodec pcm_s16le audio_files/{filename}')

generate_audio("您好，欢迎致电", "welcome.wav")
```

## 录制自己的音频

### 使用 Audacity (图形界面)
```bash
# 安装 Audacity
sudo apt-get install audacity

# 步骤:
# 1. 打开 Audacity
# 2. 点击录音按钮
# 3. 录制完成后点击停止
# 4. 文件 → 导出 → 导出为WAV
# 5. 设置:
#    - 采样率: 8000 Hz
#    - 声道: 单声道
#    - 编码: PCM 16-bit
```

### 使用命令行录音
```bash
# 使用 arecord
arecord -f S16_LE -r 8000 -c 1 -d 10 audio_files/test.wav

# -f S16_LE: 16-bit PCM
# -r 8000: 8000 Hz 采样率
# -c 1: 单声道
# -d 10: 录制10秒
```

## 音频质量检查

### 检查音频信息
```bash
# 使用 ffprobe
ffprobe audio_files/welcome.wav

# 使用 file
file audio_files/welcome.wav

# 使用 soxi
soxi audio_files/welcome.wav
```

### 播放测试
```bash
# 使用 aplay
aplay audio_files/welcome.wav

# 使用 ffplay
ffplay -nodisp -autoexit audio_files/welcome.wav

# 使用 sox
play audio_files/welcome.wav
```

### 音频可视化
```bash
# 生成波形图
sox audio_files/welcome.wav -n spectrogram -o waveform.png

# 显示音频信息
sox audio_files/welcome.wav -n stat
```

## 音频优化技巧

### 1. 降噪
```bash
# 使用 sox 降噪
sox input.wav output.wav noisered noise-profile 0.21
```

### 2. 压缩动态范围
```bash
# 让音频更均匀
sox input.wav output.wav compand 0.3,1 6:-70,-60,-20 -5 -90 0.2
```

### 3. 添加静音
```bash
# 前后各加0.5秒静音
sox input.wav output.wav pad 0.5 0.5
```

### 4. 合并多个音频
```bash
# 按顺序合并
sox part1.wav part2.wav part3.wav combined.wav

# 使用 ffmpeg 合并
echo "file 'part1.wav'" > files.txt
echo "file 'part2.wav'" >> files.txt
echo "file 'part3.wav'" >> files.txt
ffmpeg -f concat -safe 0 -i files.txt -c copy combined.wav
```

## 文件命名建议

### 清晰的命名规范
```
✅ 好的命名:
- welcome.wav
- menu_main.wav
- prompt_enter_number.wav
- confirm_order_12345.wav
- error_invalid_input.wav

❌ 不好的命名:
- audio1.wav
- test.wav
- 新录音.wav
- file (1).wav
```

### 使用前缀分类
```
audio_files/
├── greet_welcome.wav
├── greet_goodbye.wav
├── menu_main.wav
├── menu_sub1.wav
├── prompt_wait.wav
├── prompt_input.wav
├── error_invalid.wav
├── error_timeout.wav
├── confirm_success.wav
└── confirm_failed.wav
```

## 自动化音频生成脚本

```bash
#!/bin/bash
# generate_audio_files.sh

# 定义文本和文件名
declare -A texts=(
    ["welcome"]="您好，欢迎致电客服中心"
    ["menu"]="请按1查询订单，按2联系客服，按3留言"
    ["please_wait"]="请稍候，正在为您转接"
    ["thank_you"]="感谢您的来电"
    ["goodbye"]="再见"
    ["error"]="输入有误，请重试"
)

# 使用 gTTS 生成
for name in "${!texts[@]}"; do
    echo "生成: $name"
    
    # 生成 MP3
    gtts-cli "${texts[$name]}" -l zh-cn -o "/tmp/${name}.mp3"
    
    # 转换为 WAV
    ffmpeg -i "/tmp/${name}.mp3" \
           -ar 8000 -ac 1 -acodec pcm_s16le \
           "audio_files/${name}.wav" \
           -y
    
    # 清理临时文件
    rm "/tmp/${name}.mp3"
done

echo "✓ 所有音频文件已生成"
```

## 常见问题

### Q: 音频太大怎么办？
```bash
# 降低采样率到更低（但可能影响质量）
ffmpeg -i input.wav -ar 4000 -ac 1 output.wav

# 或使用压缩格式传输，播放时转换
```

### Q: 音频有杂音？
```bash
# 使用降噪
sox input.wav output.wav noisered noise.prof 0.21

# 或使用高通滤波器去除低频噪音
sox input.wav output.wav highpass 200
```

### Q: 音量不一致？
```bash
# 标准化所有音频
for file in audio_files/*.wav; do
    ffmpeg -i "$file" -filter:a loudnorm -ar 8000 -ac 1 "/tmp/normalized.wav"
    mv "/tmp/normalized.wav" "$file"
done
```

### Q: 如何测试音频是否正常？
```bash
# 播放测试
aplay audio_files/your_file.wav

# 检查格式
file audio_files/your_file.wav
# 应该显示: RIFF (little-endian) data, WAVE audio, Microsoft PCM, 16 bit, mono 8000 Hz
```

## 示例：创建完整IVR音频包

```bash
#!/bin/bash
# create_ivr_audio_pack.sh

mkdir -p audio_files

# IVR文本内容
cat > ivr_texts.txt << 'EOF'
welcome|您好，欢迎致电XYZ公司客服中心
menu_main|请按1查询订单，按2联系客服，按3留言，按0返回上一级
menu_order|查询订单请输入订单编号，或按0返回主菜单
menu_service|客服服务：按1技术支持，按2售后服务，按3投诉建议
please_wait|请稍候，正在为您查询
please_hold|请稍等，正在为您转接人工客服
transferring|正在转接，请保持通话
voicemail|您好，现在是非工作时间，请在听到提示音后留言
recording_beep|嘟
thank_you|感谢您的来电，祝您生活愉快
goodbye|再见
error_invalid|输入有误，请重新输入
error_timeout|您已超时未输入，正在返回主菜单
service_unavailable|抱歉，系统繁忙，请稍后再试
EOF

# 生成所有音频
while IFS='|' read -r name text; do
    echo "生成: $name.wav"
    
    # 使用 gTTS 生成 (需要安装: pip3 install gtts)
    python3 << PYTHON
from gtts import gTTS
tts = gTTS(text='$text', lang='zh-cn')
tts.save('/tmp/${name}.mp3')
PYTHON
    
    # 转换为电话格式
    ffmpeg -i "/tmp/${name}.mp3" \
           -ar 8000 -ac 1 -acodec pcm_s16le \
           -filter:a loudnorm \
           "audio_files/${name}.wav" \
           -y -loglevel error
    
    rm "/tmp/${name}.mp3"
done < ivr_texts.txt

echo "✓ IVR音频包创建完成"
echo "文件位置: audio_files/"
ls -lh audio_files/
```

---

## 总结

1. **标准格式**: WAV, 8000Hz, 单声道, 16-bit
2. **转换工具**: FFmpeg (推荐), SoX
3. **生成方式**: TTS (gTTS, Azure), 录音, 转换现有音频
4. **命名规范**: 清晰、分类、英文
5. **质量检查**: 播放测试、格式验证、音量标准化

现在你可以开始准备音频文件了！🎵

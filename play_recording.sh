#!/bin/bash
# 播放最新的录音文件

RECORDINGS_DIR="/home/henry/pjproject/recordings"

# 找到最新的录音
LATEST=$(ls -t "$RECORDINGS_DIR"/*.wav 2>/dev/null | head -1)

if [ -z "$LATEST" ]; then
    echo "没有找到录音文件"
    exit 1
fi

echo "播放最新录音: $LATEST"
echo ""
echo "按 Ctrl+C 停止播放"
echo ""

# 尝试使用不同的播放器
if command -v ffplay &> /dev/null; then
    ffplay -nodisp -autoexit "$LATEST"
elif command -v aplay &> /dev/null; then
    aplay "$LATEST"
elif command -v paplay &> /dev/null; then
    paplay "$LATEST"
else
    echo "错误: 未找到音频播放器 (ffplay, aplay, paplay)"
    echo ""
    echo "文件位置: $LATEST"
    echo "文件大小: $(du -h "$LATEST" | cut -f1)"
    echo ""
    echo "请使用以下命令安装播放器:"
    echo "  apt install ffmpeg        # 安装ffplay"
    echo "  apt install alsa-utils    # 安装aplay"
fi

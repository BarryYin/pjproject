#!/bin/bash
# 双向语音通信系统 - 快速启动脚本

echo "=========================================="
echo "  双向语音通信系统 - 快速启动"
echo "=========================================="
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "✗ Python3 未安装"
    exit 1
fi

echo "✓ Python3: $(python3 --version)"

# 检查PJSUA
if ! python3 -c "import pjsua" 2>/dev/null; then
    echo "✗ PJSUA模块未安装"
    echo "  请先编译安装PJSIP Python绑定"
    exit 1
fi

echo "✓ PJSUA模块: 已安装"

# 创建必要目录
mkdir -p audio_files
mkdir -p recordings

echo "✓ 目录已创建"
echo ""

# 选择模式
echo "选择启动模式:"
echo "  1) 音频队列模式 (推荐 - 服务器环境)"
echo "  2) 麦克风模式 (需要音频设备)"
echo "  3) 混合模式 (队列 + 录制)"
echo ""

read -p "请选择 (1-3, 默认1): " mode_choice

case $mode_choice in
    2)
        MODE="microphone"
        echo ""
        echo "⚠ 麦克风模式需要:"
        echo "  - 可用的麦克风设备"
        echo "  - 可用的扬声器设备"
        echo ""
        ;;
    3)
        MODE="hybrid"
        ;;
    *)
        MODE="audio_queue"
        ;;
esac

echo "启动模式: $MODE"
echo ""

# 检查音频文件
audio_count=$(ls -1 audio_files/*.wav 2>/dev/null | wc -l)
echo "音频文件: $audio_count 个"

if [ $audio_count -eq 0 ]; then
    echo ""
    echo "⚠ 提示: audio_files/ 目录为空"
    echo "  建议添加音频文件，参考: AUDIO_FILES_README.md"
    echo ""
fi

# 启动系统
echo "=========================================="
echo "  正在启动系统..."
echo "=========================================="
echo ""

python3 sip_two_way_voice.py --mode $MODE

echo ""
echo "系统已停止"

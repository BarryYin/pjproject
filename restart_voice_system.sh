#!/bin/bash
# 重启双向语音系统

echo "正在停止现有进程..."

# 查找并停止所有相关进程
pkill -f "sip_two_way_voice.py"

sleep 2

# 检查是否还有进程
if pgrep -f "sip_two_way_voice.py" > /dev/null; then
    echo "强制停止..."
    pkill -9 -f "sip_two_way_voice.py"
    sleep 1
fi

echo "✓ 已停止"
echo ""

# 选择启动模式
echo "选择启动模式:"
echo "  1) 音频队列模式 (推荐 - 适合服务器)"
echo "  2) 混合模式 (队列 + 录制)"
echo "  3) 麦克风模式 (需要音频设备)"
echo ""

read -p "请选择 (1-3, 默认1): " choice

case $choice in
    2)
        MODE="hybrid"
        ;;
    3)
        MODE="microphone"
        echo ""
        echo "⚠ 注意: 此服务器似乎没有音频设备"
        echo "  系统会自动降级到null设备"
        echo ""
        ;;
    *)
        MODE="audio_queue"
        ;;
esac

echo "正在启动: $MODE 模式..."
echo ""

# 启动系统
python3 /home/henry/pjproject/sip_two_way_voice.py --mode $MODE

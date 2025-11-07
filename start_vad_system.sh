#!/bin/bash
# 启动WebRTC VAD系统

echo "========================================"
echo "  启动AI对话系统 (WebRTC VAD)"
echo "========================================"
echo ""

# 停止旧进程
echo "1. 清理旧进程..."
pkill -9 -f sip_ai 2>/dev/null
sleep 2
echo "   ✓ 完成"
echo ""

# 设置环境
echo "2. 设置环境..."
export OPENAI_API_KEY='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'
echo "   ✓ API Key已设置"
echo ""

# 启动
echo "3. 启动系统..."
echo ""
echo "系统启动后，在命令行输入:"
echo "  call <号码>"
echo ""
echo "例如: call 82121065486"
echo ""
cd /home/henry/pjproject
python3 sip_ai_with_webrtc_vad.py

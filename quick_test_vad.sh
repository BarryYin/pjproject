#!/bin/bash
# 快速测试VAD

echo "快速启动VAD系统..."

# 清理
pkill -9 -f sip_ai 2>/dev/null
sleep 1

# 设置环境并启动
cd /home/henry/pjproject
export OPENAI_API_KEY='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'

echo ""
echo "系统启动后，输入: call <号码>"
echo ""

python3 sip_ai_with_webrtc_vad.py

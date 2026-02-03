#!/bin/bash
# 快速测试VAD

echo "快速启动VAD系统..."

# 清理
pkill -9 -f sip_ai 2>/dev/null
sleep 1

# 设置环境并启动
cd /home/henry/pjproject
# 从环境变量加载: export OPENAI_API_KEY='<OPENAI_API_KEY>'

echo ""
echo "系统启动后，输入: call <号码>"
echo ""

python3 sip_ai_with_webrtc_vad.py

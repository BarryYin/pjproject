#!/bin/bash
# 一键启动 AI对话系统

echo "================================"
echo "  启动 AI对话系统"
echo "================================"
echo ""

# 设置环境变量
export OPENAI_API_KEY='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'

cd /home/henry/pjproject

echo "启动中..."
echo "首次启动需下载模型，请等待2-3分钟"
echo ""
echo "启动成功后访问: http://localhost:8090"
echo "按 Ctrl+C 停止"
echo ""

python3 sip_ai_conversation.py

#!/bin/bash
# 一键启动 AI对话系统

echo "================================"
echo "  启动 AI对话系统"
echo "================================"
echo ""

# 设置环境变量
# 从环境变量加载: export OPENAI_API_KEY='<OPENAI_API_KEY>'

cd /home/henry/pjproject

echo "启动中..."
echo "首次启动需下载模型，请等待2-3分钟"
echo ""
echo "启动成功后访问: http://localhost:8090"
echo "按 Ctrl+C 停止"
echo ""

python3 sip_ai_conversation.py

#!/bin/bash
# 在端口8090启动AI对话系统

echo "=========================================="
echo "  AI对话系统 - 启动 (端口8090)"
echo "=========================================="
echo ""

# 设置API Key - 从环境变量加载
if [ -z "$OPENAI_API_KEY" ]; then
    source ~/.bashrc 2>/dev/null
    if [ -z "$OPENAI_API_KEY" ]; then
        echo "⚠ 警告: OPENAI_API_KEY 未设置"
    fi
fi

echo "配置:"
echo "  端口: 8090"
echo "  访问: http://localhost:8090"
echo ""

cd /home/henry/pjproject
python3 sip_ai_conversation.py

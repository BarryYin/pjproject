#!/bin/bash
# 在端口8090启动AI对话系统

echo "=========================================="
echo "  AI对话系统 - 启动 (端口8090)"
echo "=========================================="
echo ""

# 设置API Key
if [ -z "$OPENAI_API_KEY" ]; then
    source ~/.bashrc 2>/dev/null
    if [ -z "$OPENAI_API_KEY" ]; then
        export OPENAI_API_KEY='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'
    fi
fi

echo "配置:"
echo "  端口: 8090"
echo "  访问: http://localhost:8090"
echo ""

cd /home/henry/pjproject
python3 sip_ai_conversation.py

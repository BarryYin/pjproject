#!/bin/bash
# 启动阿里云NLS集成版AI对话系统

echo "=================================="
echo "  阿里云NLS集成版 AI对话系统"
echo "=================================="
echo ""

# 检查OpenAI API Key
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠ 错误: 未设置 OPENAI_API_KEY 环境变量"
    echo ""
    echo "请先设置API Key:"
    echo "  export OPENAI_API_KEY='sk-proj-XCMmLidU_4KNH5bD...'"
    echo ""
    exit 1
fi

echo "✓ OpenAI API Key 已设置"
echo ""

# 检查NLS SDK
if [ ! -d "alibabacloud-nls-python-sdk" ]; then
    echo "⚠ 警告: 未找到阿里云NLS SDK"
    echo "请确保 alibabacloud-nls-python-sdk 目录存在"
    exit 1
fi

echo "✓ 阿里云NLS SDK 已就绪"
echo ""

# 启动系统
echo "正在启动系统..."
echo ""

python3 sip_ai_nls_integrated.py

#!/bin/bash
# 优化版拨号脚本 - WebSocket长连接复用

if [ -z "$1" ]; then
    echo "使用方法: ./call_optimized.sh <电话号码>"
    echo "示例: ./call_optimized.sh 85211111111"
    exit 1
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠ 错误: 未设置 OPENAI_API_KEY"
    exit 1
fi

python3 sip_ai_nls_optimized.py "$1"

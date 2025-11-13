#!/bin/bash
# 快速拨号脚本 - 使用NLS集成版

if [ -z "$1" ]; then
    echo "使用方法: ./call_nls.sh <电话号码>"
    echo "示例: ./call_nls.sh 85211111111"
    exit 1
fi

# 检查OpenAI API Key
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠ 错误: 未设置 OPENAI_API_KEY"
    echo "请运行: export OPENAI_API_KEY='your-key'"
    exit 1
fi

# 拨打电话
python3 sip_ai_nls_cli.py "$1"

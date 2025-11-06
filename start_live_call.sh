#!/bin/bash
# 启动双向实时通话系统

cd "$(dirname "$0")"

echo "================================"
echo "双向实时通话系统启动脚本"
echo "================================"
echo ""

# 检查端口是否被占用
if lsof -Pi :8089 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "⚠ 端口 8089 已被占用，正在清理..."
    lsof -ti:8089 | xargs kill -9 2>/dev/null
    sleep 1
fi

echo "✓ 正在启动系统..."
echo ""

python3 sip_live_call_system.py

echo ""
echo "系统已停止"

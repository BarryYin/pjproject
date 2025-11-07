#!/bin/bash
# 强制清理所有SIP系统进程和端口

echo "=========================================="
echo "  强制清理 - SIP系统"
echo "=========================================="
echo ""

echo "1️⃣  查找占用端口8089的进程..."
PORT_PID=$(ss -tlnp 2>/dev/null | grep :8089 | grep -oP 'pid=\K[0-9]+' | head -1)

if [ -n "$PORT_PID" ]; then
    echo "  发现进程: PID $PORT_PID"
    
    # 查看进程详情
    ps aux | grep $PORT_PID | grep -v grep
    echo ""
    
    echo "  正在强制终止..."
    kill -9 $PORT_PID 2>/dev/null
    sleep 1
    
    if ps -p $PORT_PID > /dev/null 2>&1; then
        echo "  ✗ 进程仍在运行，尝试sudo..."
        sudo kill -9 $PORT_PID 2>/dev/null
        sleep 1
    fi
    
    if ps -p $PORT_PID > /dev/null 2>&1; then
        echo "  ✗ 无法终止进程"
    else
        echo "  ✓ 进程已终止"
    fi
else
    echo "  未找到占用进程"
fi

echo ""

echo "2️⃣  清理所有AI对话系统进程..."
pkill -9 -f "sip_ai_conversation.py" 2>/dev/null && echo "  ✓ 已停止 sip_ai_conversation.py" || echo "  无此进程"

echo ""

echo "3️⃣  清理所有双向语音系统进程..."
pkill -9 -f "sip_two_way_voice.py" 2>/dev/null && echo "  ✓ 已停止 sip_two_way_voice.py" || echo "  无此进程"

echo ""

echo "4️⃣  清理WebSocket相关进程..."
pkill -9 -f "sip_websocket_call_system.py" 2>/dev/null && echo "  ✓ 已停止 sip_websocket_call_system.py" || echo "  无此进程"
pkill -9 -f "websocket_sip_gateway.py" 2>/dev/null && echo "  ✓ 已停止 websocket_sip_gateway.py" || echo "  无此进程"

echo ""

echo "5️⃣  清理IVR系统进程..."
pkill -9 -f "sip_ivr_system.py" 2>/dev/null && echo "  ✓ 已停止 sip_ivr_system.py" || echo "  无此进程"

echo ""

echo "6️⃣  等待端口释放..."
sleep 3

echo ""

echo "7️⃣  验证端口状态..."
if netstat -tln 2>/dev/null | grep -q ":8089" || ss -tln 2>/dev/null | grep -q ":8089"; then
    echo "  ✗ 端口8089仍被占用"
    echo ""
    echo "  详细信息:"
    netstat -tlnp 2>/dev/null | grep 8089 || ss -tlnp 2>/dev/null | grep 8089
    echo ""
    echo "  尝试手动清理:"
    echo "    PID=\$(ss -tlnp 2>/dev/null | grep :8089 | grep -oP 'pid=\K[0-9]+' | head -1)"
    echo "    sudo kill -9 \$PID"
else
    echo "  ✓ 端口8089已释放"
fi

if netstat -tln 2>/dev/null | grep -q ":8088" || ss -tln 2>/dev/null | grep -q ":8088"; then
    echo "  ⚠ 端口8088仍被占用"
else
    echo "  ✓ 端口8088已释放"
fi

echo ""

echo "8️⃣  当前Python进程状态..."
echo "SIP相关进程:"
ps aux | grep -E "sip_|websocket" | grep python | grep -v grep || echo "  无"

echo ""
echo "=========================================="
echo "  清理完成!"
echo "=========================================="
echo ""

echo "下一步:"
echo "  1. 验证端口: netstat -tln | grep 808"
echo "  2. 启动系统: ./smart_start.sh"
echo "  3. 或直接启动: python3 sip_ai_conversation.py"
echo ""

#!/bin/bash
# 启动后端 - 最简单的方式

echo "================================"
echo "  启动AI对话后端"
echo "================================"
echo ""

# 清理旧进程
echo "1. 清理旧进程..."
pkill -9 -f sip_ai_conversation.py 2>/dev/null
sleep 2
echo "   ✓ 完成"
echo ""

# 检查端口
echo "2. 检查端口8090..."
if netstat -tln 2>/dev/null | grep -q ":8090" || ss -tln 2>/dev/null | grep -q ":8090"; then
    echo "   ✗ 端口仍被占用"
    echo "   尝试强制释放..."
    PID=$(ss -tlnp 2>/dev/null | grep :8090 | grep -oP 'pid=\K[0-9]+' | head -1)
    if [ -n "$PID" ]; then
        kill -9 $PID 2>/dev/null
        sleep 2
    fi
fi
echo "   ✓ 端口可用"
echo ""

# 设置环境变量
echo "3. 设置环境..."
export OPENAI_API_KEY='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'
echo "   ✓ API Key已设置"
echo ""

# 启动后端
echo "4. 启动后端服务..."
echo ""
echo "================================"
echo "  后端正在启动..."
echo "================================"
echo ""
echo "前端页面: http://localhost:9000/test_frontend.html"
echo "后端API: http://localhost:8090"
echo ""
echo "等待看到 '✓ API服务器' 就可以用了"
echo "按 Ctrl+C 停止"
echo ""

cd /home/henry/pjproject
python3 sip_ai_conversation.py

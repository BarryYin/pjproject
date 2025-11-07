#!/bin/bash
# 检查AI系统状态

echo "=========================================="
echo "  AI对话系统 - 状态检查"
echo "=========================================="
echo ""

# 1. 检查进程
echo "1️⃣  检查进程状态:"
if pgrep -f "sip_ai_conversation.py" > /dev/null; then
    echo "  ✓ 系统正在运行"
    echo ""
    ps aux | grep "[s]ip_ai_conversation.py"
    echo ""
else
    echo "  ✗ 系统未运行"
    echo ""
    echo "启动命令:"
    echo "  ./quick_start_ai_conversation.sh"
    echo "或"
    echo "  ./restart_ai_system.sh"
    exit 1
fi

# 2. 检查端口
echo "2️⃣  检查端口8089:"
if netstat -tln 2>/dev/null | grep -q ":8089" || ss -tln 2>/dev/null | grep -q ":8089"; then
    echo "  ✓ 端口正在监听"
    netstat -tlnp 2>/dev/null | grep 8089 || ss -tlnp 2>/dev/null | grep 8089
else
    echo "  ✗ 端口未监听"
fi
echo ""

# 3. 测试Web服务
echo "3️⃣  测试Web服务:"
echo "  正在测试 http://localhost:8089 ..."

if timeout 3 curl -s http://localhost:8089/ > /dev/null 2>&1; then
    echo "  ✓ Web服务响应正常"
    echo ""
    echo "访问地址:"
    echo "  本地: http://localhost:8089"
    echo "  远程: http://$(hostname -I | awk '{print $1}'):8089"
else
    echo "  ✗ Web服务无响应"
    echo ""
    echo "可能原因:"
    echo "  1. 系统启动中（首次需下载模型，请等待）"
    echo "  2. 程序遇到错误卡住"
    echo "  3. 端口被其他进程占用"
    echo ""
    echo "建议操作:"
    echo "  1. 等待2-3分钟（首次启动）"
    echo "  2. 查看运行窗口的输出日志"
    echo "  3. 或重启系统: ./restart_ai_system.sh"
fi
echo ""

# 4. 测试API
echo "4️⃣  测试API接口:"
if timeout 3 curl -s -X POST http://localhost:8089/api/status > /dev/null 2>&1; then
    echo "  ✓ API可用"
    response=$(curl -s -X POST http://localhost:8089/api/status 2>/dev/null)
    echo "  响应: $response"
else
    echo "  ✗ API无响应"
fi
echo ""

echo "=========================================="
echo "  快速操作"
echo "=========================================="
echo ""
echo "停止系统:"
echo "  pkill -f sip_ai_conversation.py"
echo ""
echo "重启系统:"
echo "  ./restart_ai_system.sh"
echo ""
echo "查看日志:"
echo "  (查看运行窗口的输出)"
echo ""

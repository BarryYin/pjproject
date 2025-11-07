#!/bin/bash
# 重启AI对话系统

echo "=========================================="
echo "  重启 AI对话系统"
echo "=========================================="
echo ""

# 停止现有进程
echo "1️⃣  停止现有进程..."
if pgrep -f "sip_ai_conversation.py" > /dev/null; then
    pkill -f "sip_ai_conversation.py"
    sleep 2
    
    # 检查是否成功停止
    if pgrep -f "sip_ai_conversation.py" > /dev/null; then
        echo "  强制停止..."
        pkill -9 -f "sip_ai_conversation.py"
        sleep 1
    fi
    
    echo "  ✓ 已停止"
else
    echo "  没有运行的实例"
fi

echo ""

# 检查端口
echo "2️⃣  检查端口8089..."
if netstat -tln 2>/dev/null | grep -q ":8089" || ss -tln 2>/dev/null | grep -q ":8089"; then
    echo "  ⚠ 端口8089仍被占用，等待释放..."
    sleep 3
    
    if netstat -tln 2>/dev/null | grep -q ":8089" || ss -tln 2>/dev/null | grep -q ":8089"; then
        echo "  ✗ 端口未释放，可能需要手动处理"
        exit 1
    fi
fi

echo "  ✓ 端口可用"
echo ""

# 设置环境变量
echo "3️⃣  设置环境..."
if [ -z "$OPENAI_API_KEY" ]; then
    # 从bashrc加载
    if grep -q "OPENAI_API_KEY" ~/.bashrc; then
        source ~/.bashrc
        echo "  ✓ API Key已加载"
    else
        echo "  ⚠ API Key未设置"
        read -p "  输入OpenAI API Key (或按Enter跳过): " api_key
        if [ -n "$api_key" ]; then
            export OPENAI_API_KEY="$api_key"
            echo "  ✓ API Key已设置（临时）"
        fi
    fi
else
    echo "  ✓ API Key已就绪"
fi

echo ""
echo "=========================================="
echo "  启动 AI对话系统..."
echo "=========================================="
echo ""

# 启动系统
cd /home/henry/pjproject
python3 sip_ai_conversation.py

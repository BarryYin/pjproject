#!/bin/bash
# 修复并启动AI系统

echo "=========================================="
echo "  修复并启动 AI对话系统"
echo "=========================================="
echo ""

# 1. 停止所有相关进程
echo "1️⃣  清理旧进程..."
pkill -9 -f sip_ai_conversation.py 2>/dev/null
pkill -9 -f sip_two_way_voice.py 2>/dev/null
sleep 2
echo "  ✓ 已清理"
echo ""

# 2. 检查端口
echo "2️⃣  检查端口..."
max_wait=10
count=0
while netstat -tln 2>/dev/null | grep -q ":8089" || ss -tln 2>/dev/null | grep -q ":8089"; do
    echo "  等待端口8089释放... ($count/$max_wait)"
    sleep 1
    count=$((count+1))
    if [ $count -ge $max_wait ]; then
        echo "  ⚠ 端口释放超时，继续尝试..."
        break
    fi
done
echo "  ✓ 端口已释放"
echo ""

# 3. 加载环境变量
echo "3️⃣  加载环境..."
if [ -z "$OPENAI_API_KEY" ]; then
    source ~/.bashrc 2>/dev/null
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "  ⚠ 未找到OPENAI_API_KEY"
    echo "  设置临时key..."
    # 从环境变量加载: export OPENAI_API_KEY='<OPENAI_API_KEY>'
fi
echo "  ✓ API Key已就绪"
echo ""

# 4. 启动系统
echo "=========================================="
echo "  启动系统..."
echo "=========================================="
echo ""
echo "首次启动会下载Whisper模型（约2-3分钟）"
echo "请耐心等待..."
echo ""
echo "启动后访问: http://localhost:8089"
echo ""
echo "按 Ctrl+C 停止系统"
echo ""

cd /home/henry/pjproject
python3 sip_ai_conversation.py

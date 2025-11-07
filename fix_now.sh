#!/bin/bash
# 立即修复 - 停止卡住的进程并正确启动

echo "================================"
echo "  立即修复并启动"
echo "================================"
echo ""

echo "1️⃣  停止卡住的进程..."
pkill -9 -f sip_ai_conversation.py
sleep 2
echo "✓ 已停止"
echo ""

echo "2️⃣  检查端口..."
if netstat -tln 2>/dev/null | grep -q ":8090" || ss -tln 2>/dev/null | grep -q ":8090"; then
    echo "⚠ 端口仍被占用，等待..."
    sleep 3
fi
echo "✓ 端口已释放"
echo ""

echo "3️⃣  预下载模型（重要！避免页面卡住）"
echo "这会下载Whisper模型，需要2-3分钟..."
echo "请耐心等待，这是一次性的！"
echo ""

export OPENAI_API_KEY='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'

python3 /home/henry/pjproject/download_models.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ 模型已下载!"
    echo ""
else
    echo ""
    echo "⚠ 模型下载有问题，但继续..."
    echo ""
fi

echo "4️⃣  现在启动系统（会很快！）"
echo ""
echo "启动后访问: http://localhost:8090"
echo "按 Ctrl+C 停止"
echo ""

cd /home/henry/pjproject
python3 sip_ai_conversation.py

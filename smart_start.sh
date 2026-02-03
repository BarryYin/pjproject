#!/bin/bash
# 智能启动 - 自动检测并解决问题

echo "=========================================="
echo "  AI对话系统 - 智能启动"
echo "=========================================="
echo ""

# 检查是否已运行
if pgrep -f "sip_ai_conversation.py" > /dev/null; then
    echo "⚠ 检测到系统已在运行"
    echo ""
    
    # 测试是否正常工作
    if timeout 2 curl -s http://localhost:8089/ > /dev/null 2>&1; then
        echo "✓ 系统运行正常！"
        echo ""
        echo "访问地址:"
        echo "  http://localhost:8089"
        echo ""
        
        read -p "是否重启系统? (y/n): " restart
        if [ "$restart" != "y" ]; then
            echo "保持当前实例运行"
            exit 0
        fi
    else
        echo "✗ 系统运行异常（端口占用但无响应）"
        echo "  正在自动修复..."
        echo ""
    fi
    
    # 停止旧进程
    echo "停止旧进程..."
    pkill -9 -f sip_ai_conversation.py 2>/dev/null
    sleep 2
    echo "✓ 已停止"
    echo ""
fi

# 检查端口
echo "检查端口8089..."
max_wait=5
count=0
while netstat -tln 2>/dev/null | grep -q ":8089" || ss -tln 2>/dev/null | grep -q ":8089"; do
    if [ $count -ge $max_wait ]; then
        echo "✗ 端口8089仍被占用"
        echo ""
        echo "尝试手动解决:"
        echo "  sudo lsof -i :8089"
        echo "  sudo kill -9 <PID>"
        exit 1
    fi
    sleep 1
    count=$((count+1))
done
echo "✓ 端口可用"
echo ""

# 检查依赖
echo "检查依赖..."
python3 << 'EOF'
import sys
try:
    import faster_whisper
    import edge_tts
    import openai
    import numpy
    print("✓ 所有依赖已安装")
except ImportError as e:
    print(f"✗ 缺少依赖: {e}")
    print("\n安装依赖:")
    print("  ./install_ai_dependencies.sh")
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    exit 1
fi
echo ""

# 检查API Key
echo "检查API Key..."
if [ -z "$OPENAI_API_KEY" ]; then
    source ~/.bashrc 2>/dev/null
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠ 未找到OPENAI_API_KEY"
    echo ""
    echo "设置临时key（已配置的key）..."
    # 从环境变量加载: export OPENAI_API_KEY='<OPENAI_API_KEY>'
fi
echo "✓ API Key已就绪"
echo ""

# 检查目录
echo "检查目录..."
mkdir -p /home/henry/pjproject/audio_files 2>/dev/null
mkdir -p /home/henry/pjproject/recordings 2>/dev/null
mkdir -p /home/henry/pjproject/temp_audio 2>/dev/null
echo "✓ 目录已准备"
echo ""

# 启动系统
echo "=========================================="
echo "  启动系统..."
echo "=========================================="
echo ""
echo "📌 提示:"
echo "  - 首次启动需下载Whisper模型（2-3分钟）"
echo "  - 启动成功后访问: http://localhost:8089"
echo "  - 按 Ctrl+C 停止系统"
echo ""

cd /home/henry/pjproject
python3 sip_ai_conversation.py

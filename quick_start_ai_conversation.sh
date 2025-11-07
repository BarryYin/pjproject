#!/bin/bash
# AI智能对话系统 - 快速启动

echo "=========================================="
echo "  AI智能对话系统 - 快速启动"
echo "=========================================="
echo ""

# 检查依赖
echo "检查依赖..."

check_python_package() {
    python3 -c "import $1" 2>/dev/null
    return $?
}

all_deps_ok=true

if check_python_package "faster_whisper"; then
    echo "  ✓ faster-whisper"
else
    echo "  ✗ faster-whisper - 未安装"
    all_deps_ok=false
fi

if check_python_package "edge_tts"; then
    echo "  ✓ edge-tts"
else
    echo "  ✗ edge-tts - 未安装"
    all_deps_ok=false
fi

if check_python_package "openai"; then
    echo "  ✓ openai"
else
    echo "  ✗ openai - 未安装"
    all_deps_ok=false
fi

if ! $all_deps_ok; then
    echo ""
    echo "⚠ 依赖未完全安装"
    read -p "是否现在安装? (y/n): " install_deps
    
    if [ "$install_deps" = "y" ]; then
        ./install_ai_dependencies.sh
    else
        echo "请手动运行: ./install_ai_dependencies.sh"
        exit 1
    fi
fi

echo ""

# 检查OpenAI API Key
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠ 未设置 OPENAI_API_KEY"
    echo ""
    read -p "输入 OpenAI API Key (或按Enter跳过): " api_key
    
    if [ -n "$api_key" ]; then
        export OPENAI_API_KEY="$api_key"
        echo "✓ API Key 已设置（临时）"
        echo ""
        echo "提示: 永久设置请运行:"
        echo "  echo \"export OPENAI_API_KEY='$api_key'\" >> ~/.bashrc"
    else
        echo "⚠ 未设置API Key，AI功能将使用默认回复"
    fi
else
    echo "✓ OPENAI_API_KEY 已设置"
fi

echo ""

# 检查当前运行的实例
if pgrep -f "sip_ai_conversation.py" > /dev/null; then
    echo "⚠ 检测到系统已在运行"
    echo ""
    ps aux | grep "[s]ip_ai_conversation.py"
    echo ""
    read -p "是否停止现有实例? (y/n): " stop_existing
    
    if [ "$stop_existing" = "y" ]; then
        echo "正在停止..."
        pkill -f "sip_ai_conversation.py"
        sleep 2
        echo "✓ 已停止"
    else
        echo "保持现有实例运行"
        exit 0
    fi
fi

echo ""
echo "=========================================="
echo "  正在启动 AI智能对话系统..."
echo "=========================================="
echo ""
echo "配置:"
echo "  ASR: faster-whisper (base模型)"
echo "  TTS: Edge TTS (印尼语)"
echo "  AI: GPT-3.5-turbo"
echo "  端口: 8089"
echo ""
echo "启动后访问: http://localhost:8089"
echo ""
echo "按 Ctrl+C 停止系统"
echo ""

# 启动系统
python3 /home/henry/pjproject/sip_ai_conversation.py

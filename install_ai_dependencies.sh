#!/bin/bash
# 安装AI对话系统依赖

echo "=========================================="
echo "  AI智能对话系统 - 依赖安装"
echo "=========================================="
echo ""

# 检查Python版本
echo "1️⃣  检查Python版本..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "  Python版本: $python_version"

# 安装系统依赖
echo ""
echo "2️⃣  安装系统依赖..."
echo "  (ffmpeg - 音频转换)"

if ! command -v ffmpeg &> /dev/null; then
    echo "  正在安装 ffmpeg..."
    sudo apt-get update -qq
    sudo apt-get install -y ffmpeg
else
    echo "  ✓ ffmpeg 已安装"
fi

# 安装Python包
echo ""
echo "3️⃣  安装Python依赖包..."
echo ""

echo "  [1/4] faster-whisper (ASR引擎)..."
pip3 install faster-whisper -q
if [ $? -eq 0 ]; then
    echo "  ✓ faster-whisper 安装成功"
else
    echo "  ✗ faster-whisper 安装失败"
fi

echo ""
echo "  [2/4] edge-tts (TTS引擎)..."
pip3 install edge-tts -q
if [ $? -eq 0 ]; then
    echo "  ✓ edge-tts 安装成功"
else
    echo "  ✗ edge-tts 安装失败"
fi

echo ""
echo "  [3/4] openai (AI引擎)..."
pip3 install openai -q
if [ $? -eq 0 ]; then
    echo "  ✓ openai 安装成功"
else
    echo "  ✗ openai 安装失败"
fi

echo ""
echo "  [4/4] numpy (音频处理)..."
pip3 install numpy -q
if [ $? -eq 0 ]; then
    echo "  ✓ numpy 安装成功"
else
    echo "  ✗ numpy 安装失败"
fi

# 验证安装
echo ""
echo "=========================================="
echo "  验证安装"
echo "=========================================="
echo ""

python3 << 'EOF'
import sys

packages = {
    'faster_whisper': 'faster-whisper',
    'edge_tts': 'edge-tts',
    'openai': 'openai',
    'numpy': 'numpy'
}

all_ok = True
for module, name in packages.items():
    try:
        __import__(module)
        print(f"  ✓ {name}")
    except ImportError:
        print(f"  ✗ {name} - 未安装")
        all_ok = False

if all_ok:
    print("\n✓ 所有依赖已安装!")
else:
    print("\n⚠ 部分依赖安装失败")
    sys.exit(1)
EOF

# OpenAI API Key 提示
echo ""
echo "=========================================="
echo "  配置 OpenAI API Key"
echo "=========================================="
echo ""

if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠ 未设置 OPENAI_API_KEY"
    echo ""
    echo "请设置环境变量:"
    echo "  export OPENAI_API_KEY='your-api-key-here'"
    echo ""
    echo "或添加到 ~/.bashrc:"
    echo "  echo \"export OPENAI_API_KEY='your-key'\" >> ~/.bashrc"
    echo "  source ~/.bashrc"
    echo ""
    
    read -p "是否现在设置? (y/n): " set_key
    if [ "$set_key" = "y" ]; then
        read -p "输入你的 OpenAI API Key: " api_key
        echo "export OPENAI_API_KEY='$api_key'" >> ~/.bashrc
        export OPENAI_API_KEY="$api_key"
        echo "✓ API Key 已设置并保存到 ~/.bashrc"
    fi
else
    echo "✓ OPENAI_API_KEY 已设置"
fi

# 测试faster-whisper模型下载
echo ""
echo "=========================================="
echo "  下载 Whisper 模型"
echo "=========================================="
echo ""

echo "首次使用时会自动下载模型，请耐心等待..."
echo "模型大小:"
echo "  - tiny: ~75MB"
echo "  - base: ~142MB (推荐)"
echo "  - small: ~466MB"
echo ""

read -p "是否现在预下载 base 模型? (y/n): " download_model

if [ "$download_model" = "y" ]; then
    python3 << 'EOF'
print("正在下载 Whisper base 模型...")
try:
    from faster_whisper import WhisperModel
    model = WhisperModel("base", device="cpu", compute_type="int8")
    print("✓ 模型下载成功")
except Exception as e:
    print(f"✗ 模型下载失败: {e}")
EOF
fi

echo ""
echo "=========================================="
echo "  安装完成!"
echo "=========================================="
echo ""
echo "现在可以启动系统:"
echo "  python3 sip_ai_conversation.py"
echo ""
echo "或使用快速启动脚本:"
echo "  ./quick_start_ai_conversation.sh"
echo ""

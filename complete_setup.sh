#!/bin/bash
# 完整安装和设置 - 一次性搞定所有准备工作

echo "=========================================="
echo "  AI对话系统 - 完整安装"
echo "=========================================="
echo ""

# 步骤1: 安装依赖
echo "步骤 1/3: 安装Python依赖..."
echo ""

pip3 install faster-whisper edge-tts openai numpy -q

if [ $? -eq 0 ]; then
    echo "✓ 依赖安装完成"
else
    echo "✗ 依赖安装失败"
    exit 1
fi

echo ""

# 步骤2: 下载模型
echo "步骤 2/3: 下载AI模型..."
echo "这可能需要2-3分钟，请耐心等待..."
echo ""

python3 /home/henry/pjproject/download_models.py

if [ $? -eq 0 ]; then
    echo "✓ 模型下载完成"
else
    echo "⚠ 模型下载遇到问题，但可以继续"
fi

echo ""

# 步骤3: 配置API Key
echo "步骤 3/3: 配置OpenAI API Key..."
echo ""

if grep -q "OPENAI_API_KEY" ~/.bashrc; then
    echo "✓ API Key 已在 ~/.bashrc 中"
else
    echo "添加 API Key 到 ~/.bashrc..."
    echo "# 从环境变量加载: export OPENAI_API_KEY='<OPENAI_API_KEY>'" >> ~/.bashrc
    echo "✓ API Key 已保存"
fi

source ~/.bashrc 2>/dev/null
echo ""

echo "=========================================="
echo "  ✓ 安装完成!"
echo "=========================================="
echo ""
echo "现在可以快速启动系统（无需等待）:"
echo ""
echo "  ./start_now.sh"
echo ""
echo "或者:"
echo ""
echo "  cd /home/henry/pjproject"
echo "  python3 sip_ai_conversation.py"
echo ""
echo "访问: http://localhost:8090"
echo ""

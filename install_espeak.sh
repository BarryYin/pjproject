#!/bin/bash
# 安装espeak用于本地TTS

echo "安装espeak（本地TTS）..."
sudo apt-get update -qq
sudo apt-get install -y espeak

echo ""
echo "测试espeak:"
espeak --version

echo ""
echo "测试印尼语:"
espeak -v id "Halo, ini adalah tes" --stdout > /tmp/test_espeak.wav 2>&1
ls -lh /tmp/test_espeak.wav

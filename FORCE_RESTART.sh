#!/bin/bash

echo "========================================"
echo "  强制重启 AI 对话系统"
echo "========================================"

# 1. 杀掉所有Python进程
echo ""
echo "[1/5] 杀掉所有相关进程..."
pkill -9 -f sip_ai_nls_optimized.py
pkill -9 -f python3.*sip_ai
sleep 2

# 2. 确认没有残留
echo "[2/5] 确认进程已停止..."
PROC_COUNT=$(ps aux | grep -c "[s]ip_ai_nls_optimized")
if [ $PROC_COUNT -gt 0 ]; then
    echo "  ⚠ 仍有 $PROC_COUNT 个进程在运行，再次强制杀掉..."
    ps aux | grep "[s]ip_ai_nls_optimized" | awk '{print $2}' | xargs kill -9
    sleep 1
fi
echo "  ✅ 所有进程已停止"

# 3. 清理Python缓存
echo "[3/5] 清理Python缓存..."
find /home/henry/pjproject -name "*.pyc" -delete 2>/dev/null
find /home/henry/pjproject -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
echo "  ✅ 缓存已清理"

# 4. 验证配置
echo "[4/5] 验证最新配置..."
grep "smart_interrupt_enabled" /home/henry/pjproject/sip_ai_nls_optimized.py | head -1
grep "vad_min_speech_frames" /home/henry/pjproject/sip_ai_nls_optimized.py | head -1
grep "self.min_interval = " /home/henry/pjproject/sip_ai_nls_optimized.py | head -2

# 5. 完成
echo ""
echo "[5/5] ✅ 准备完成！"
echo ""
echo "=========================================="
echo "  配置验证"
echo "=========================================="
echo "智能打断: 应该是 False"
echo "VAD最小帧: 应该是 10"
echo "限流间隔: 应该是 3.0"
echo ""
echo "现在执行："
echo "  ./call_optimized.sh <电话号码>"
echo "=========================================="

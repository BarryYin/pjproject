#!/bin/bash
# 重启AI对话系统

echo "=========================================="
echo "  重启AI对话系统"
echo "=========================================="

# 1. 停止现有进程
echo ""
echo "[1/4] 停止现有进程..."
pkill -f sip_ai_nls_optimized.py
sleep 1

# 2. 清理Python缓存
echo "[2/4] 清理Python缓存..."
find /home/henry/pjproject -name "*.pyc" -delete 2>/dev/null
find /home/henry/pjproject -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null

# 3. 验证代码
echo "[3/4] 验证代码..."
python3 check_version.py

# 4. 准备就绪
echo ""
echo "[4/4] ✅ 准备就绪！"
echo ""
echo "现在可以启动系统了："
echo "  ./call_optimized.sh <电话号码>"
echo ""

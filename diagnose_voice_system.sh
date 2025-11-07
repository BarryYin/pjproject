#!/bin/bash
# 诊断双向语音系统

echo "=========================================="
echo "  双向语音系统 - 诊断工具"
echo "=========================================="
echo ""

# 1. 检查进程
echo "1️⃣  检查运行状态:"
if pgrep -f "sip_two_way_voice.py" > /dev/null; then
    echo "  ✓ 系统正在运行"
    ps aux | grep "[s]ip_two_way_voice.py"
else
    echo "  ✗ 系统未运行"
fi
echo ""

# 2. 检查端口
echo "2️⃣  检查端口8088:"
if netstat -tln 2>/dev/null | grep -q ":8088" || ss -tln 2>/dev/null | grep -q ":8088"; then
    echo "  ✓ 端口8088正在监听"
    netstat -tlnp 2>/dev/null | grep 8088 || ss -tlnp 2>/dev/null | grep 8088
else
    echo "  ✗ 端口8088未监听"
fi
echo ""

# 3. 检查Web服务
echo "3️⃣  检查Web服务:"
if curl -s -m 2 http://localhost:8088/ > /dev/null 2>&1; then
    echo "  ✓ Web服务响应正常"
    echo "  访问: http://localhost:8088"
else
    echo "  ✗ Web服务无响应"
    echo "  可能原因:"
    echo "    - 系统启动时卡住"
    echo "    - 音频设备问题"
    echo "    - 端口被占用"
fi
echo ""

# 4. 检查音频设备
echo "4️⃣  检查音频设备:"
if command -v aplay > /dev/null 2>&1; then
    echo "  ✓ aplay 可用"
    aplay -l 2>&1 | head -5
else
    echo "  ✗ aplay 不可用 (无音频工具)"
fi

if command -v arecord > /dev/null 2>&1; then
    echo "  ✓ arecord 可用"
else
    echo "  ✗ arecord 不可用 (无录音工具)"
fi
echo ""

# 5. 检查目录
echo "5️⃣  检查目录结构:"
if [ -d "/home/henry/pjproject/audio_files" ]; then
    audio_count=$(ls -1 /home/henry/pjproject/audio_files/*.wav 2>/dev/null | wc -l)
    echo "  ✓ audio_files/ 存在 ($audio_count 个WAV文件)"
else
    echo "  ✗ audio_files/ 不存在"
fi

if [ -d "/home/henry/pjproject/recordings" ]; then
    record_count=$(ls -1 /home/henry/pjproject/recordings/*.wav 2>/dev/null | wc -l)
    echo "  ✓ recordings/ 存在 ($record_count 个录音)"
else
    echo "  ✗ recordings/ 不存在"
fi
echo ""

# 6. 测试API
echo "6️⃣  测试API接口:"
if curl -s -m 2 -X POST http://localhost:8088/api/status 2>/dev/null | grep -q "success"; then
    echo "  ✓ API响应正常"
    echo "  状态:"
    curl -s -X POST http://localhost:8088/api/status 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "  (无法解析JSON)"
else
    echo "  ✗ API无响应"
fi
echo ""

# 7. 推荐操作
echo "=========================================="
echo "  推荐操作:"
echo "=========================================="

if ! pgrep -f "sip_two_way_voice.py" > /dev/null; then
    echo "  1) 启动系统:"
    echo "     ./restart_voice_system.sh"
elif ! curl -s -m 2 http://localhost:8088/ > /dev/null 2>&1; then
    echo "  1) 系统可能卡住，建议重启:"
    echo "     pkill -f sip_two_way_voice.py"
    echo "     python3 sip_two_way_voice.py --mode audio_queue"
else
    echo "  ✓ 系统运行正常"
    echo "  访问控制面板: http://localhost:8088"
fi

if ! command -v aplay > /dev/null 2>&1; then
    echo ""
    echo "  ⚠ 提示: 此服务器无音频设备"
    echo "     推荐使用: 音频队列模式 或 混合模式"
    echo "     不推荐: 麦克风模式"
fi

echo ""

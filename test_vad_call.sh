#!/bin/bash
# 测试VAD系统呼叫

if [ -z "$1" ]; then
    echo "用法: $0 <电话号码>"
    echo "示例: $0 82121065486"
    exit 1
fi

PHONE=$1

echo "测试WebRTC VAD系统..."
echo ""

# 发起呼叫
echo "拨号: $PHONE"
curl -X POST http://localhost:8090/api/call \
  -H "Content-Type: application/json" \
  -d "{\"phone_number\": \"$PHONE\"}" \
  2>/dev/null | python3 -m json.tool

echo ""
echo "呼叫已发起，系统会自动:"
echo "  1. 接通电话"
echo "  2. 播放欢迎语"
echo "  3. 实时监听对方说话"
echo "  4. VAD检测语音结束"
echo "  5. ASR识别"
echo "  6. AI生成回复"
echo "  7. TTS合成并播放"
echo ""
echo "查看后端终端的实时日志了解VAD检测情况"
echo ""
echo "日志示例:"
echo "  [VAD] 🎤 检测到说话"
echo "  [VAD] ✓ 句子结束"
echo "  [ASR] '用户说的话'"
echo "  [AI] 'AI的回复'"

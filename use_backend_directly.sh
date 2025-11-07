#!/bin/bash
# 直接使用后端 - 无需前端

echo "========================================"
echo "  AI对话系统 - 命令行控制"
echo "========================================"
echo ""

API="http://localhost:8090"

# 检查后端
echo "检查后端状态..."
STATUS=$(curl -s -X POST $API/api/status)
if [ $? -eq 0 ]; then
    echo "✓ 后端运行正常"
    echo ""
else
    echo "✗ 后端未运行"
    echo "请先启动: ./start_backend.sh"
    exit 1
fi

# 菜单
while true; do
    echo ""
    echo "================================"
    echo "  操作菜单"
    echo "================================"
    echo "1. 发起AI对话呼叫"
    echo "2. 挂断当前呼叫"
    echo "3. 查看系统状态"
    echo "4. 添加音频到队列"
    echo "5. 立即播放音频"
    echo "6. 退出"
    echo ""
    read -p "选择操作 (1-6): " choice
    
    case $choice in
        1)
            echo ""
            read -p "输入电话号码: " phone
            if [ -n "$phone" ]; then
                echo "正在发起呼叫..."
                RESULT=$(curl -s -X POST $API/api/call \
                    -H "Content-Type: application/json" \
                    -d "{\"phone_number\": \"$phone\"}")
                echo "响应: $RESULT"
            fi
            ;;
        2)
            echo ""
            echo "正在挂断..."
            RESULT=$(curl -s -X POST $API/api/hangup)
            echo "响应: $RESULT"
            ;;
        3)
            echo ""
            echo "系统状态:"
            curl -s -X POST $API/api/status | python3 -m json.tool
            ;;
        4)
            echo ""
            read -p "输入音频文件名: " audio
            if [ -n "$audio" ]; then
                echo "正在添加到队列..."
                RESULT=$(curl -s -X POST $API/api/add_audio \
                    -H "Content-Type: application/json" \
                    -d "{\"filename\": \"$audio\"}")
                echo "响应: $RESULT"
            fi
            ;;
        5)
            echo ""
            read -p "输入音频文件名: " audio
            if [ -n "$audio" ]; then
                echo "正在播放..."
                RESULT=$(curl -s -X POST $API/api/play_now \
                    -H "Content-Type: application/json" \
                    -d "{\"filename\": \"$audio\"}")
                echo "响应: $RESULT"
            fi
            ;;
        6)
            echo ""
            echo "退出"
            exit 0
            ;;
        *)
            echo "无效选择"
            ;;
    esac
done

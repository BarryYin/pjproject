#!/bin/bash
# 检查最近一次通话的录音

echo "========================================"
echo "  检查最近一次通话"
echo "========================================"
echo ""

# 1. 分析录音
echo "📊 分析录音文件..."
python3 analyze_recording.py

echo ""
echo "========================================"
echo ""

# 2. 询问是否提取语音段
read -p "是否提取语音段? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "🎵 提取语音段..."
    python3 extract_voice_segments.py
    
    echo ""
    echo "========================================"
    echo ""
    
    # 3. 询问是否播放
    read -p "是否播放语音段? (y/n) " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        SEGMENTS=$(ls -t recordings/*_segment_*.wav 2>/dev/null | head -6)
        
        if [ -z "$SEGMENTS" ]; then
            echo "未找到语音段文件"
        else
            for segment in $SEGMENTS; do
                echo "播放: $segment"
                
                if command -v ffplay &> /dev/null; then
                    ffplay -nodisp -autoexit "$segment" 2>/dev/null
                elif command -v aplay &> /dev/null; then
                    aplay "$segment" 2>/dev/null
                else
                    echo "未找到音频播放器"
                    break
                fi
                
                echo ""
            done
        fi
    fi
fi

echo ""
echo "✓ 完成"

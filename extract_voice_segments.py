#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提取录音中的语音段
自动提取有声音的部分，去除静音
"""

import sys
import wave
import struct
import os

def extract_voice_segments(input_file, output_prefix=None, threshold_percent=10):
    """提取语音段并保存为单独的文件"""
    
    if not os.path.exists(input_file):
        print(f"✗ 文件不存在: {input_file}")
        return
    
    if output_prefix is None:
        output_prefix = os.path.splitext(input_file)[0] + "_segment"
    
    print(f"\n提取语音段: {os.path.basename(input_file)}\n")
    
    try:
        with wave.open(input_file, 'rb') as wav:
            params = wav.getparams()
            channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            framerate = wav.getframerate()
            n_frames = wav.getnframes()
            
            # 读取所有数据
            frames = wav.readframes(n_frames)
            
            # 解析样本
            if sample_width == 2:
                fmt = f"{n_frames * channels}h"
                samples = struct.unpack(fmt, frames)
            else:
                print(f"✗ 不支持的采样位宽: {sample_width}")
                return
            
            # 计算阈值
            max_amplitude = max(abs(min(samples)), abs(max(samples)))
            voice_threshold = max_amplitude * (threshold_percent / 100)
            
            print(f"最大振幅: {max_amplitude}")
            print(f"语音阈值: {voice_threshold:.0f} ({threshold_percent}%)")
            print()
            
            # 检测语音段（每0.1秒为一个块）
            chunk_size = int(framerate * channels * 0.1)  # 0.1秒
            segments = []
            in_voice = False
            segment_start = 0
            
            for i in range(0, len(samples), chunk_size):
                chunk = samples[i:i+chunk_size]
                if not chunk:
                    break
                
                chunk_max = max(abs(min(chunk)), abs(max(chunk)))
                
                if chunk_max > voice_threshold:
                    if not in_voice:
                        segment_start = i
                        in_voice = True
                else:
                    if in_voice:
                        # 添加一些缓冲（前后各0.2秒）
                        buffer_samples = int(framerate * channels * 0.2)
                        start = max(0, segment_start - buffer_samples)
                        end = min(len(samples), i + buffer_samples)
                        segments.append((start, end))
                        in_voice = False
            
            # 添加最后一段
            if in_voice:
                buffer_samples = int(framerate * channels * 0.2)
                start = max(0, segment_start - buffer_samples)
                end = len(samples)
                segments.append((start, end))
            
            print(f"找到 {len(segments)} 个语音段\n")
            
            if not segments:
                print("未检测到语音段")
                return
            
            # 保存每个语音段
            for i, (start, end) in enumerate(segments, 1):
                segment_samples = samples[start:end]
                segment_frames = struct.pack(f"{len(segment_samples)}h", *segment_samples)
                
                output_file = f"{output_prefix}_{i}.wav"
                
                with wave.open(output_file, 'wb') as out_wav:
                    out_wav.setparams(params)
                    out_wav.writeframes(segment_frames)
                
                duration = len(segment_samples) / (framerate * channels)
                start_time = start / (framerate * channels)
                
                print(f"段 {i}:")
                print(f"  时间: {start_time:.1f}s - {start_time + duration:.1f}s")
                print(f"  时长: {duration:.2f}秒")
                print(f"  文件: {output_file}")
                print(f"  大小: {os.path.getsize(output_file):,} 字节")
                print()
            
            print(f"✓ 完成！提取了 {len(segments)} 个语音段")
            
    except Exception as e:
        print(f"✗ 提取失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    if len(sys.argv) < 2:
        print("用法: python3 extract_voice_segments.py <录音文件> [阈值百分比]")
        print("示例: python3 extract_voice_segments.py recordings/call_xxx.wav 10")
        print()
        
        # 尝试处理最新的录音
        recordings_dir = "/home/henry/pjproject/recordings"
        if os.path.exists(recordings_dir):
            files = [os.path.join(recordings_dir, f) 
                    for f in os.listdir(recordings_dir) 
                    if f.endswith('.wav')]
            if files:
                files.sort(key=os.path.getmtime, reverse=True)
                print(f"处理最新的录音: {os.path.basename(files[0])}\n")
                extract_voice_segments(files[0])
                return
        
        sys.exit(1)
    
    input_file = sys.argv[1]
    threshold = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    extract_voice_segments(input_file, threshold_percent=threshold)


if __name__ == "__main__":
    main()

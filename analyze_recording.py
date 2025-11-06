#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
录音文件分析工具
功能:
1. 检测录音中是否有语音活动
2. 显示音频波形统计
3. 检测静音段和说话段
"""

import sys
import wave
import struct
import os

def analyze_wav_file(filename):
    """分析WAV文件"""
    
    if not os.path.exists(filename):
        print(f"✗ 文件不存在: {filename}")
        return
    
    print(f"\n{'='*70}")
    print(f"录音文件分析: {os.path.basename(filename)}")
    print(f"{'='*70}\n")
    
    try:
        with wave.open(filename, 'rb') as wav:
            # 获取音频参数
            channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            framerate = wav.getframerate()
            n_frames = wav.getnframes()
            duration = n_frames / framerate
            
            print("文件信息:")
            print(f"  声道数: {channels}")
            print(f"  采样位宽: {sample_width * 8} bit")
            print(f"  采样率: {framerate} Hz")
            print(f"  总帧数: {n_frames}")
            print(f"  时长: {duration:.2f} 秒")
            print()
            
            # 读取所有音频数据
            print("正在分析音频数据...")
            frames = wav.readframes(n_frames)
            
            # 解析为样本值
            if sample_width == 1:
                fmt = f"{n_frames * channels}B"
                samples = struct.unpack(fmt, frames)
                samples = [s - 128 for s in samples]  # 转换为有符号
            elif sample_width == 2:
                fmt = f"{n_frames * channels}h"
                samples = struct.unpack(fmt, frames)
            else:
                print(f"✗ 不支持的采样位宽: {sample_width}")
                return
            
            # 统计分析
            total_samples = len(samples)
            max_amplitude = max(abs(min(samples)), abs(max(samples)))
            avg_amplitude = sum(abs(s) for s in samples) / total_samples
            
            # 计算RMS（均方根）
            rms = (sum(s**2 for s in samples) / total_samples) ** 0.5
            
            # 检测语音活动
            silence_threshold = max_amplitude * 0.05  # 5%的最大振幅作为静音阈值
            voice_threshold = max_amplitude * 0.1     # 10%的最大振幅作为语音阈值
            
            silent_samples = sum(1 for s in samples if abs(s) < silence_threshold)
            voice_samples = sum(1 for s in samples if abs(s) > voice_threshold)
            
            silent_percent = (silent_samples / total_samples) * 100
            voice_percent = (voice_samples / total_samples) * 100
            
            print("\n音频统计:")
            print(f"  最大振幅: {max_amplitude}")
            print(f"  平均振幅: {avg_amplitude:.2f}")
            print(f"  RMS值: {rms:.2f}")
            print()
            
            print("语音活动分析:")
            print(f"  静音采样点: {silent_samples:,} ({silent_percent:.1f}%)")
            print(f"  语音采样点: {voice_samples:,} ({voice_percent:.1f}%)")
            print()
            
            # 判断是否有语音
            if max_amplitude < 100:
                print("⚠ 警告: 音频几乎完全静音（最大振幅 < 100）")
                print("   可能的原因:")
                print("   1. 麦克风未开启或音量太小")
                print("   2. 音频设备未正确连接")
                print("   3. 对方未说话或静音")
            elif voice_percent < 5:
                print("⚠ 警告: 检测到极少语音活动")
                print("   可能对方说话很少或音量很小")
            elif voice_percent < 20:
                print("✓ 检测到一些语音活动")
                print("  可能对方说话较少或音量较小")
            else:
                print("✓ 检测到明显的语音活动")
                print("  录音中包含正常的对话内容")
            
            # 检测连续语音段
            print("\n语音段检测:")
            in_voice = False
            voice_start = 0
            voice_segments = []
            
            # 按秒分析
            samples_per_second = framerate * channels
            for i in range(0, len(samples), samples_per_second):
                chunk = samples[i:i+samples_per_second]
                if not chunk:
                    break
                    
                chunk_max = max(abs(min(chunk)), abs(max(chunk)))
                
                if chunk_max > voice_threshold:
                    if not in_voice:
                        voice_start = i // samples_per_second
                        in_voice = True
                else:
                    if in_voice:
                        voice_end = i // samples_per_second
                        voice_segments.append((voice_start, voice_end))
                        in_voice = False
            
            # 添加最后一段
            if in_voice:
                voice_segments.append((voice_start, int(duration)))
            
            if voice_segments:
                print(f"  找到 {len(voice_segments)} 个语音段:")
                for i, (start, end) in enumerate(voice_segments[:10]):  # 只显示前10个
                    print(f"    段{i+1}: {start}s - {end}s (时长: {end-start}s)")
                if len(voice_segments) > 10:
                    print(f"    ... 还有 {len(voice_segments)-10} 个语音段")
            else:
                print("  未检测到明显的语音段")
            
            # 音频质量评估
            print("\n音频质量评估:")
            if max_amplitude > 30000:
                print("  ⚠ 可能存在音频削波（过载）")
            elif max_amplitude < 500:
                print("  ⚠ 音频电平太低")
            else:
                print("  ✓ 音频电平正常")
            
            # 建议
            print("\n建议:")
            if max_amplitude < 100:
                print("  1. 检查PJSIP会议桥连接是否正确")
                print("  2. 确认对方电话已接通并在说话")
                print("  3. 检查录音器连接的音频源")
            elif voice_percent > 50:
                print("  ✓ 录音质量良好，可以播放查看内容")
            else:
                print("  录音可能包含大量静音，建议检查通话质量")
            
            print()
            
    except wave.Error as e:
        print(f"✗ WAV文件错误: {e}")
    except Exception as e:
        print(f"✗ 分析失败: {e}")
        import traceback
        traceback.print_exc()


def list_recordings(directory="/home/henry/pjproject/recordings"):
    """列出所有录音文件"""
    
    if not os.path.exists(directory):
        print(f"✗ 录音目录不存在: {directory}")
        return []
    
    files = [f for f in os.listdir(directory) if f.endswith('.wav')]
    
    if not files:
        print(f"\n录音目录中没有WAV文件: {directory}")
        return []
    
    files.sort(reverse=True)  # 最新的在前
    
    print(f"\n{'='*70}")
    print(f"录音文件列表 ({len(files)} 个文件)")
    print(f"{'='*70}\n")
    
    for i, filename in enumerate(files[:20], 1):  # 只显示最新的20个
        filepath = os.path.join(directory, filename)
        size = os.path.getsize(filepath)
        mtime = os.path.getmtime(filepath)
        
        import time
        timestr = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
        
        print(f"  [{i:2d}] {filename}")
        print(f"       时间: {timestr}")
        print(f"       大小: {size:,} 字节 ({size/1024:.1f} KB)")
        print()
    
    if len(files) > 20:
        print(f"  ... 还有 {len(files)-20} 个文件\n")
    
    return [os.path.join(directory, f) for f in files]


def main():
    """主函数"""
    
    if len(sys.argv) > 1:
        # 分析指定的文件
        filename = sys.argv[1]
        analyze_wav_file(filename)
    else:
        # 列出并分析最新的录音
        files = list_recordings()
        
        if files:
            print("分析最新的录音文件...")
            analyze_wav_file(files[0])
            
            print(f"\n{'='*70}")
            print("使用方法:")
            print(f"  python3 {sys.argv[0]} <录音文件路径>")
            print(f"  例如: python3 {sys.argv[0]} recordings/call_20231106_123456.wav")
            print(f"{'='*70}\n")


if __name__ == "__main__":
    main()

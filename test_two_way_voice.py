#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双向语音系统测试脚本
测试不同模式的功能
"""

import requests
import time
import sys
import os

API_BASE = "http://localhost:8088/api"

def print_section(title):
    """打印分隔标题"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")

def check_system():
    """检查系统是否运行"""
    try:
        response = requests.post(f"{API_BASE}/status", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ 系统运行正常")
            print(f"  模式: {data.get('mode')}")
            print(f"  活动呼叫: {data.get('has_active_call')}")
            return True
    except:
        print("✗ 系统未运行或无法连接")
        print("  请先启动: python3 sip_two_way_voice.py")
        return False

def test_audio_queue_mode(phone_number):
    """测试音频队列模式"""
    print_section("测试: 音频队列模式")
    
    print("1️⃣  切换到音频队列模式...")
    response = requests.post(f"{API_BASE}/switch_mode", 
                            json={"mode": "audio_queue"})
    print(f"   {response.json()}")
    time.sleep(1)
    
    print("\n2️⃣  发起呼叫...")
    response = requests.post(f"{API_BASE}/call", 
                            json={"phone_number": phone_number})
    print(f"   {response.json()}")
    
    print("\n3️⃣  等待呼叫接通...")
    for i in range(10):
        time.sleep(1)
        response = requests.post(f"{API_BASE}/status")
        status = response.json()
        
        if status.get('call_connected'):
            print("   ✓ 呼叫已接通!")
            break
        print(f"   等待中... ({i+1}/10)")
    else:
        print("   ✗ 超时: 呼叫未接通")
        return
    
    print("\n4️⃣  添加音频到队列...")
    test_audios = ["test1.wav", "test2.wav", "test3.wav"]
    
    for audio in test_audios:
        response = requests.post(f"{API_BASE}/add_audio", 
                                json={"filename": audio})
        result = response.json()
        if result.get('success'):
            print(f"   ✓ 已添加: {audio} (队列: {result.get('queue_size')})")
        else:
            print(f"   ⚠ 添加失败: {audio} - {result.get('error')}")
        time.sleep(0.5)
    
    print("\n5️⃣  测试立即播放...")
    response = requests.post(f"{API_BASE}/play_now", 
                            json={"filename": "urgent.wav"})
    result = response.json()
    if result.get('success'):
        print(f"   ✓ {result.get('message')}")
    else:
        print(f"   ⚠ {result.get('error')}")
    
    print("\n6️⃣  等待播放完成...")
    time.sleep(10)
    
    print("\n7️⃣  挂断呼叫...")
    response = requests.post(f"{API_BASE}/hangup")
    print(f"   {response.json()}")
    
    print("\n✓ 音频队列模式测试完成")

def test_microphone_mode(phone_number):
    """测试麦克风模式"""
    print_section("测试: 麦克风模式")
    
    print("⚠ 注意: 此模式需要音频设备（麦克风和扬声器）")
    print("  请确保:")
    print("    1. 有可用的麦克风")
    print("    2. 有可用的扬声器")
    print("    3. 系统已重启到麦克风模式")
    print()
    
    input("按Enter继续测试，或Ctrl+C取消...")
    
    print("\n1️⃣  切换到麦克风模式...")
    response = requests.post(f"{API_BASE}/switch_mode", 
                            json={"mode": "microphone"})
    result = response.json()
    
    if not result.get('success'):
        print("   ✗ 切换失败（可能有活动呼叫）")
        print("   请手动重启系统到麦克风模式:")
        print("   python3 sip_two_way_voice.py --mode microphone")
        return
    
    print(f"   {result}")
    time.sleep(1)
    
    print("\n2️⃣  发起呼叫...")
    response = requests.post(f"{API_BASE}/call", 
                            json={"phone_number": phone_number})
    print(f"   {response.json()}")
    
    print("\n3️⃣  等待呼叫接通...")
    for i in range(10):
        time.sleep(1)
        response = requests.post(f"{API_BASE}/status")
        status = response.json()
        
        if status.get('call_connected'):
            print("   ✓ 呼叫已接通!")
            break
        print(f"   等待中... ({i+1}/10)")
    else:
        print("   ✗ 超时: 呼叫未接通")
        return
    
    print("\n4️⃣  现在可以实时通话...")
    print("   - 对着麦克风说话，对方会听到")
    print("   - 对方声音会从扬声器输出")
    print()
    
    duration = 30
    print(f"   测试时长: {duration}秒")
    for i in range(duration):
        time.sleep(1)
        print(f"   通话中... {i+1}/{duration}秒", end='\r')
    
    print("\n\n5️⃣  挂断呼叫...")
    response = requests.post(f"{API_BASE}/hangup")
    print(f"   {response.json()}")
    
    print("\n✓ 麦克风模式测试完成")

def test_hybrid_mode(phone_number):
    """测试混合模式"""
    print_section("测试: 混合模式")
    
    print("1️⃣  切换到混合模式...")
    response = requests.post(f"{API_BASE}/switch_mode", 
                            json={"mode": "hybrid"})
    print(f"   {response.json()}")
    time.sleep(1)
    
    print("\n2️⃣  发起呼叫...")
    response = requests.post(f"{API_BASE}/call", 
                            json={"phone_number": phone_number})
    print(f"   {response.json()}")
    
    print("\n3️⃣  等待呼叫接通...")
    for i in range(10):
        time.sleep(1)
        response = requests.post(f"{API_BASE}/status")
        status = response.json()
        
        if status.get('call_connected'):
            print("   ✓ 呼叫已接通!")
            break
        print(f"   等待中... ({i+1}/10)")
    else:
        print("   ✗ 超时: 呼叫未接通")
        return
    
    print("\n4️⃣  添加音频队列...")
    test_audios = ["question1.wav", "question2.wav"]
    
    for audio in test_audios:
        response = requests.post(f"{API_BASE}/add_audio", 
                                json={"filename": audio})
        result = response.json()
        if result.get('success'):
            print(f"   ✓ 已添加: {audio}")
        else:
            print(f"   ⚠ {result.get('error')}")
        time.sleep(0.5)
    
    print("\n5️⃣  播放问题并录制回答...")
    print("   系统会:")
    print("   - 播放预录问题")
    print("   - 录制对方回答")
    
    time.sleep(15)
    
    print("\n6️⃣  挂断呼叫...")
    response = requests.post(f"{API_BASE}/hangup")
    print(f"   {response.json()}")
    
    print("\n7️⃣  检查录音文件...")
    recordings_dir = "/home/henry/pjproject/recordings"
    if os.path.exists(recordings_dir):
        files = sorted([f for f in os.listdir(recordings_dir) if f.endswith('.wav')])
        if files:
            latest = files[-1]
            print(f"   ✓ 最新录音: {latest}")
            print(f"   位置: {recordings_dir}/{latest}")
        else:
            print("   ⚠ 未找到录音文件")
    else:
        print("   ⚠ 录音目录不存在")
    
    print("\n✓ 混合模式测试完成")

def interactive_test():
    """交互式测试"""
    print_section("交互式测试模式")
    
    print("可用命令:")
    print("  1 - 拨号")
    print("  2 - 挂断")
    print("  3 - 添加音频")
    print("  4 - 立即播放")
    print("  5 - 查看状态")
    print("  6 - 切换模式")
    print("  q - 退出")
    print()
    
    while True:
        cmd = input("\n> 输入命令: ").strip()
        
        if cmd == 'q':
            break
        
        elif cmd == '1':
            phone = input("  输入号码: ").strip()
            if phone:
                response = requests.post(f"{API_BASE}/call", 
                                        json={"phone_number": phone})
                print(f"  {response.json()}")
        
        elif cmd == '2':
            response = requests.post(f"{API_BASE}/hangup")
            print(f"  {response.json()}")
        
        elif cmd == '3':
            filename = input("  音频文件名: ").strip()
            if filename:
                response = requests.post(f"{API_BASE}/add_audio", 
                                        json={"filename": filename})
                print(f"  {response.json()}")
        
        elif cmd == '4':
            filename = input("  音频文件名: ").strip()
            if filename:
                response = requests.post(f"{API_BASE}/play_now", 
                                        json={"filename": filename})
                print(f"  {response.json()}")
        
        elif cmd == '5':
            response = requests.post(f"{API_BASE}/status")
            status = response.json()
            print("  系统状态:")
            print(f"    模式: {status.get('mode')}")
            print(f"    活动呼叫: {status.get('has_active_call')}")
            print(f"    已接通: {status.get('call_connected')}")
            print(f"    队列长度: {status.get('queue_size')}")
        
        elif cmd == '6':
            print("  模式: microphone / audio_queue / hybrid")
            mode = input("  选择模式: ").strip()
            if mode in ['microphone', 'audio_queue', 'hybrid']:
                response = requests.post(f"{API_BASE}/switch_mode", 
                                        json={"mode": mode})
                print(f"  {response.json()}")
        
        else:
            print("  ✗ 未知命令")

def main():
    """主测试函数"""
    print_section("双向语音系统 - 测试工具")
    
    # 检查系统
    if not check_system():
        sys.exit(1)
    
    print("\n选择测试模式:")
    print("  1 - 音频队列模式测试")
    print("  2 - 麦克风模式测试")
    print("  3 - 混合模式测试")
    print("  4 - 完整测试（所有模式）")
    print("  5 - 交互式测试")
    print("  q - 退出")
    
    choice = input("\n选择 (1-5): ").strip()
    
    if choice == 'q':
        return
    
    # 除了交互式测试外，都需要电话号码
    if choice in ['1', '2', '3', '4']:
        phone_number = input("\n输入测试电话号码 (例如: 82121065486): ").strip()
        if not phone_number:
            print("✗ 未输入号码")
            return
        
        if choice == '1':
            test_audio_queue_mode(phone_number)
        elif choice == '2':
            test_microphone_mode(phone_number)
        elif choice == '3':
            test_hybrid_mode(phone_number)
        elif choice == '4':
            print("\n📋 开始完整测试...")
            test_audio_queue_mode(phone_number)
            time.sleep(3)
            test_hybrid_mode(phone_number)
            print("\n⚠ 麦克风模式需要重启系统，请手动测试")
    
    elif choice == '5':
        interactive_test()
    
    else:
        print("✗ 无效选择")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n中断测试")
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")

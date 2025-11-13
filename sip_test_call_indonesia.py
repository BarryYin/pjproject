#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIP拨号测试脚本 - 印度尼西亚线路
SIP服务器配置:
- 服务器: 147.139.205.88:5060
- 主叫号码: 6281479242434
- 被叫前缀: 13462
- 送量格式: 13462+号码
"""

import sys
import time
import pjsua as pj
import threading
import select

LOG_LEVEL = 4

class CallCallback(pj.CallCallback):
    """呼叫回调处理"""
    
    def __init__(self, call=None):
        pj.CallCallback.__init__(self, call)
        self.call_connected = False
        self.call_ended = False
        self.call_start_time = time.time()
        self.ring_time = None
        self.answer_time = None
        
    def on_state(self):
        """呼叫状态变化"""
        info = self.call.info()
        current_time = time.time()
        elapsed = current_time - self.call_start_time
        
        print(f"\n[呼叫状态] {info.remote_uri}")
        print(f"  状态: {info.state_text}")
        print(f"  代码: {info.last_code} ({info.last_reason})")
        print(f"  耗时: {elapsed:.1f}秒")
        
        # 详细状态说明
        if info.state == pj.CallState.CALLING:
            print("  >>> 正在发起呼叫...")
            
        elif info.state == pj.CallState.EARLY:
            if self.ring_time is None:
                self.ring_time = current_time
            ring_elapsed = current_time - self.ring_time
            if info.last_code == 180:
                print(f"  >>> 对方振铃中... (已振铃 {ring_elapsed:.1f}秒)")
            elif info.last_code == 183:
                print(f"  >>> 会话进行中... (已等待 {ring_elapsed:.1f}秒)")
            else:
                print(f"  >>> 早期状态: {info.last_code}")
            
        elif info.state == pj.CallState.CONNECTING:
            print("  >>> 正在连接...")
            
        elif info.state == pj.CallState.CONFIRMED:
            self.call_connected = True
            self.answer_time = current_time
            if self.ring_time:
                ring_duration = self.answer_time - self.ring_time
                print(f"  >>> ✓ 呼叫已接通! (振铃 {ring_duration:.1f}秒)")
            else:
                print("  >>> ✓ 呼叫已接通!")
            
        elif info.state == pj.CallState.DISCONNECTED:
            self.call_ended = True
            total_duration = current_time - self.call_start_time
            
            # 详细的挂断原因分析
            print(f"  >>> 呼叫已结束 (总时长 {total_duration:.1f}秒)")
            
            if info.last_code == 200:
                print("  原因: 正常挂断")
            elif info.last_code == 486:
                print("  原因: 用户忙")
            elif info.last_code == 487:
                print("  原因: 请求已取消")
            elif info.last_code == 480:
                print("  原因: 暂时无法接通")
            elif info.last_code == 404:
                print("  原因: 号码不存在")
            elif info.last_code == 403:
                print("  原因: 禁止呼叫")
            elif info.last_code == 408:
                print("  原因: 请求超时")
            elif info.last_code == 603:
                print("  原因: 拒绝接听")
            else:
                print(f"  原因: {info.last_reason}")
                
            if self.call_connected and self.answer_time:
                talk_time = current_time - self.answer_time
                print(f"  通话时长: {talk_time:.1f}秒")
            
    def on_media_state(self):
        """媒体状态变化"""
        info = self.call.info()
        if info.media_state == pj.MediaState.ACTIVE:
            call_slot = info.conf_slot
            pj.Lib.instance().conf_connect(call_slot, 0)
            pj.Lib.instance().conf_connect(0, call_slot)
            print("\n[媒体] 音频通道已激活")
        else:
            print(f"\n[媒体] 媒体状态: {info.media_state}")


def log_cb(level, str_log, len):
    """日志回调"""
    print(str_log, end='')


def check_system_audio():
    """检查系统音频配置"""
    import subprocess
    
    print("\n" + "=" * 60)
    print("系统音频检测")
    print("=" * 60)
    
    # 检查PulseAudio
    try:
        result = subprocess.run(['pactl', 'list', 'sinks', 'short'], 
                              capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            sinks = result.stdout.strip().split('\n')
            print(f"\n[PulseAudio 输出设备] 共 {len(sinks)} 个:")
            for sink in sinks:
                parts = sink.split('\t')
                if len(parts) >= 2:
                    dev_name = parts[1]
                    print(f"  - {dev_name}")
                    if 'null' in dev_name.lower():
                        print("    ⚠ 警告: 这是虚拟设备，不会产生真实声音!")
    except Exception:
        pass
    
    # 检查PulseAudio输入
    try:
        result = subprocess.run(['pactl', 'list', 'sources', 'short'], 
                              capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            sources = result.stdout.strip().split('\n')
            print(f"\n[PulseAudio 输入设备] 共 {len(sources)} 个:")
            for source in sources:
                parts = source.split('\t')
                if len(parts) >= 2:
                    dev_name = parts[1]
                    print(f"  - {dev_name}")
                    if 'null' in dev_name.lower() or 'monitor' in dev_name.lower():
                        print("    ⚠ 警告: 这是虚拟设备!")
    except Exception:
        pass
    
    # 检查ALSA
    try:
        result = subprocess.run(['aplay', '-l'], 
                              capture_output=True, text=True, timeout=2)
        if result.returncode == 0 and result.stdout:
            print("\n[ALSA 输出设备]:")
            print(result.stdout[:500])
    except Exception:
        pass
    
    print()


def list_audio_devices(lib):
    """列出PJSUA音频设备"""
    print("\n" + "=" * 60)
    print("PJSUA 音频设备")
    print("=" * 60)
    
    devices = []
    
    try:
        # 尝试获取音频设备数量（不同PJSUA版本API不同）
        if hasattr(lib, 'enum_snd_dev'):
            # 新版本API
            devices = lib.enum_snd_dev()
            
            if not devices:
                print("\n⚠ 警告: 未检测到音频设备!")
                return None, None
            
            print(f"\n✓ 检测到 {len(devices)} 个音频设备:\n")
            
            for i, dev in enumerate(devices):
                print(f"  [{i}] {dev.name}")
                print(f"      输入通道: {dev.input_count}")
                print(f"      输出通道: {dev.output_count}")
                if 'null' in dev.name.lower():
                    print("      ⚠ 虚拟设备 - 不会产生真实声音!")
                print()
            
            return devices, True
            
        else:
            # 旧版本API不支持枚举
            print("\n✓ PJSUA版本较旧，无法列出设备")
            print("  将使用系统默认设备")
            return None, False
        
    except Exception as e:
        print(f"\n⚠ 音频设备检测失败: {e}")
        print("  将使用系统默认设备")
        return None, False


def input_thread_func(call_obj):
    """按键输入处理线程"""
    print("\n可用命令:")
    print("  h - 挂断电话")
    print("  m - 切换静音")
    print("  i - 显示通话信息")
    print("  q - 退出")
    print()
    
    while call_obj.get('active', False):
        try:
            # 检查是否有输入
            if select.select([sys.stdin], [], [], 0.5)[0]:
                key = sys.stdin.readline().strip().lower()
                
                if key == 'h':
                    print("\n[操作] 挂断电话...")
                    call_obj['hangup'] = True
                    break
                    
                elif key == 'q':
                    print("\n[操作] 退出程序...")
                    call_obj['hangup'] = True
                    break
                    
                elif key == 'm':
                    current_call = call_obj.get('call')
                    if current_call:
                        try:
                            # 先检查呼叫是否有效
                            if not current_call.is_valid():
                                print("\n[错误] 呼叫已失效")
                                continue
                                
                            info = current_call.info()
                            # 检查呼叫是否还在活动状态
                            if info.state != pj.CallState.CONFIRMED:
                                print("\n[错误] 呼叫未在通话状态")
                                continue
                            
                            # 切换静音状态
                            call_obj['muted'] = not call_obj.get('muted', False)
                            if call_obj['muted']:
                                # 断开麦克风
                                pj.Lib.instance().conf_disconnect(0, info.conf_slot)
                                print("\n[操作] 已静音")
                            else:
                                # 连接麦克风
                                pj.Lib.instance().conf_connect(0, info.conf_slot)
                                print("\n[操作] 取消静音")
                        except Exception as e:
                            print(f"\n[错误] 静音操作失败: {e}")
                            
                elif key == 'i':
                    current_call = call_obj.get('call')
                    if current_call:
                        try:
                            # 先检查呼叫是否有效
                            if not current_call.is_valid():
                                print("\n[错误] 呼叫已失效")
                                continue
                                
                            info = current_call.info()
                            print("\n[通话信息]")
                            print(f"  状态: {info.state_text}")
                            print(f"  被叫: {info.remote_uri}")
                            print(f"  持续时间: {info.connect_duration.sec}秒")
                            print(f"  媒体状态: {info.media_state}")
                        except Exception as e:
                            print(f"\n[错误] 获取信息失败: {e}")
                            
        except Exception as e:
            print(f"\n[错误] 输入处理异常: {e}")
            break


def make_test_call(destination_number, country_code="62", call_timeout=60):
    """
    发起测试呼叫 - 印度尼西亚线路
    
    参数:
        destination_number: 目标号码
        country_code: 国家码,默认62(印度尼西亚)
        call_timeout: 呼叫超时时间(秒),默认60秒
    """
    
    # SIP服务器配置 - 印度尼西亚线路
    SERVER = "147.139.205.88"
    SIP_PORT = 5060
    PREFIX = "13462"
    CALLER_NUMBER = "6281479242434"  # 主叫号码
    
    # 构造完整号码: 前缀+号码
    full_number = f"{PREFIX}{destination_number}"
    sip_uri = f"sip:{full_number}@{SERVER}:{SIP_PORT}"
    
    print("=" * 60)
    print("SIP 测试呼叫配置 - 印度尼西亚线路")
    print("=" * 60)
    print(f"服务器: {SERVER}:{SIP_PORT}")
    print(f"主叫号码: {CALLER_NUMBER}")
    print(f"被叫前缀: {PREFIX}")
    print(f"目标号码: {destination_number}")
    print(f"完整被叫: {full_number}")
    print(f"SIP URI: {sip_uri}")
    print("=" * 60)
    
    lib = None
    current_call = None
    input_thread = None
    call_control = {'active': False, 'hangup': False, 'call': None, 'muted': False}
    
    try:
        # 创建库实例
        lib = pj.Lib()
        
        # 配置音频
        media_cfg = pj.MediaConfig()
        media_cfg.enable_ice = False
        media_cfg.snd_auto_close_time = 1
        media_cfg.no_vad = True  # 禁用VAD提高音质
        media_cfg.ec_tail_len = 200  # 回声消除
        media_cfg.clock_rate = 8000  # 标准语音采样率
        
        # 初始化库
        lib.init(
            log_cfg=pj.LogConfig(level=LOG_LEVEL, callback=log_cb),
            media_cfg=media_cfg
        )
        
        # 先检查系统音频
        check_system_audio()
        
        # 检查PJSUA音频设备
        devices, has_enum = list_audio_devices(lib)
        
        # 设置音频设备
        capture_dev = -1  # 输入设备（麦克风）
        playback_dev = -1  # 输出设备（扬声器）
        
        # 如果可以枚举设备，让用户选择或自动选择最佳设备
        if devices and has_enum:
            # 查找第一个非null设备
            real_dev_idx = None
            for i, dev in enumerate(devices):
                if 'null' not in dev.name.lower() and dev.input_count > 0 and dev.output_count > 0:
                    real_dev_idx = i
                    break
            
            if real_dev_idx is not None:
                capture_dev = real_dev_idx
                playback_dev = real_dev_idx
                print(f"\n✓ 自动选择设备 [{real_dev_idx}]: {devices[real_dev_idx].name}")
            else:
                print("\n⚠ 未找到真实音频设备，使用默认设备（可能无声音）")
        
        try:
            lib.set_snd_dev(capture_dev, playback_dev)
            if capture_dev == -1:
                print("\n✓ 音频设备已配置（使用系统默认）")
            else:
                print("✓ 音频设备配置成功")
        except Exception as e:
            print(f"\n⚠ 音频设备配置失败: {e}")
            print("  将尝试使用默认设备")
        
        # 创建UDP传输
        transport = lib.create_transport(
            pj.TransportType.UDP,
            pj.TransportConfig(0)
        )
        
        print(f"\n[传输] 本地监听: {transport.info().host}:{transport.info().port}")
        
        # 启动库
        lib.start()
        
        # 创建本地账户配置(设置主叫显示号码)
        acc_cfg = pj.AccountConfig()
        acc_cfg.id = f"sip:{CALLER_NUMBER}@{SERVER}:{SIP_PORT}"
        acc_cfg.reg_uri = ""  # 不注册
        
        # 创建账户
        acc = lib.create_account(acc_cfg)
        
        print("\n[准备] 正在发起呼叫...")
        
        # 发起呼叫
        call_cb = CallCallback()
        current_call = acc.make_call(sip_uri, cb=call_cb)
        
        # 设置呼叫控制对象
        call_control['active'] = True
        call_control['call'] = current_call
        
        print(f"\n呼叫超时设置: {call_timeout}秒")
        
        # 启动输入处理线程
        input_thread = threading.Thread(target=input_thread_func, args=(call_control,), daemon=True)
        input_thread.start()
        
        print("-" * 60)
        
        # 等待呼叫结束或超时
        call_start = time.time()
        last_warning_time = 0
        
        while True:
            elapsed = time.time() - call_start
            
            # 检查用户是否要求挂断
            if call_control.get('hangup', False):
                print("\n[用户操作] 挂断呼叫")
                try:
                    if current_call:
                        current_call.hangup()
                except pj.Error as e:
                    print(f"挂断失败: {e}")
                break
            
            # 检查呼叫是否结束（安全检查）
            try:
                if not current_call or not current_call.is_valid():
                    print("\n呼叫已失效")
                    break
                    
                if current_call.info().state == pj.CallState.DISCONNECTED:
                    print("\n呼叫已结束")
                    break
            except Exception as e:
                print(f"\n呼叫状态检查异常: {e}")
                break
            
            # 超时检查
            if elapsed >= call_timeout:
                print(f"\n[超时] 呼叫超过 {call_timeout} 秒，自动挂断")
                try:
                    current_call.hangup()
                except pj.Error as e:
                    print(f"挂断失败: {e}")
                break
            
            # 定期提示状态（每10秒）
            if elapsed - last_warning_time >= 10 and not call_cb.call_connected:
                remaining = call_timeout - elapsed
                print(f"\n[提示] 呼叫进行中... (已用时 {elapsed:.0f}秒, 剩余 {remaining:.0f}秒)")
                last_warning_time = elapsed
            
            time.sleep(1)
        
        # 停止输入线程
        call_control['active'] = False
            
    except pj.Error as e:
        print(f"\n[错误] PJSUA异常: {e}")
        return False
        
    except KeyboardInterrupt:
        print("\n\n[退出] 用户中断")
        
    finally:
        # 清理
        if current_call:
            try:
                # 安全检查呼叫是否有效
                if current_call.is_valid():
                    info = current_call.info()
                    if info.state != pj.CallState.DISCONNECTED:
                        print("\n[清理] 挂断呼叫...")
                        current_call.hangup()
                        time.sleep(1)
            except Exception as e:
                print(f"[清理] 挂断异常: {e}")
                pass
                
        if lib:
            print("[清理] 销毁库...")
            try:
                lib.destroy()
            except Exception:
                pass
                
    return True


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("PJSIP 呼叫测试工具 - 印度尼西亚线路")
    print("=" * 60 + "\n")
    
    if len(sys.argv) < 2:
        print("用法:")
        print(f"  {sys.argv[0]} <目标号码> [超时秒数]")
        print("\n示例:")
        print(f"  {sys.argv[0]} 81234567890           # 拨打印尼号码(默认60秒超时)")
        print(f"  {sys.argv[0]} 6281234567890         # 拨打完整印尼号码")
        print(f"  {sys.argv[0]} 81234567890 30        # 设置30秒超时")
        print("\n配置信息:")
        print("  服务器: 147.139.205.88:5060")
        print("  主叫号码: 6281479242434")
        print("  被叫格式: 13462 + 号码")
        print("  示例: 13462 81234567890")
        print("  默认超时: 60秒")
        sys.exit(1)
    
    destination = sys.argv[1]
    timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    
    make_test_call(destination, call_timeout=timeout)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全版本的SIP拨号测试 - 修复call_id断言失败问题
"""

import sys
import time
import pjsua as pj
import threading

LOG_LEVEL = 3

class SafeCallCallback(pj.CallCallback):
    """安全的呼叫回调处理"""
    
    def __init__(self, call=None):
        pj.CallCallback.__init__(self, call)
        self.call_connected = False
        self.call_ended = False
        self.lock = threading.Lock()
        
    def is_call_valid(self):
        """检查呼叫是否有效"""
        try:
            with self.lock:
                if not self.call:
                    return False
                if not self.call.is_valid():
                    return False
                return True
        except:
            return False
            
    def on_state(self):
        """呼叫状态变化"""
        try:
            if not self.is_call_valid():
                return
                
            with self.lock:
                info = self.call.info()
                
                print(f"\n[状态] {info.state_text} - {info.last_code} {info.last_reason}")
                
                if info.state == pj.CallState.CONFIRMED:
                    self.call_connected = True
                    print("  >>> ✓ 呼叫已接通!")
                    
                elif info.state == pj.CallState.DISCONNECTED:
                    self.call_ended = True
                    print(f"  >>> 呼叫已结束")
                    if info.last_code == 200:
                        print("  原因: 正常挂断")
                    else:
                        print(f"  原因: {info.last_reason}")
                        
        except Exception as e:
            print(f"[错误] 状态回调异常: {e}")
            
    def on_media_state(self):
        """媒体状态变化"""
        try:
            if not self.is_call_valid():
                return
                
            with self.lock:
                info = self.call.info()
                
                if info.media_state == pj.MediaState.ACTIVE:
                    call_slot = info.conf_slot
                    lib = pj.Lib.instance()
                    lib.conf_connect(call_slot, 0)
                    lib.conf_connect(0, call_slot)
                    print("\n[媒体] 音频通道已激活")
                    
        except Exception as e:
            print(f"[错误] 媒体回调异常: {e}")


def make_safe_call(destination, timeout=60):
    """
    发起安全的测试呼叫
    """
    
    SERVER = "147.139.205.88"
    SIP_PORT = 5060
    PREFIX = "13462"
    CALLER = "6281479242434"
    
    full_number = f"{PREFIX}{destination}"
    sip_uri = f"sip:{full_number}@{SERVER}:{SIP_PORT}"
    
    print("=" * 60)
    print("安全版本 SIP 测试呼叫")
    print("=" * 60)
    print(f"目标号码: {destination}")
    print(f"完整号码: {full_number}")
    print(f"SIP URI: {sip_uri}")
    print(f"超时时间: {timeout}秒")
    print("=" * 60)
    
    lib = None
    current_call = None
    call_cb = None
    
    try:
        # 创建库
        lib = pj.Lib()
        
        # 简单配置
        lib.init(log_cfg=pj.LogConfig(level=LOG_LEVEL))
        
        # 创建传输
        transport = lib.create_transport(pj.TransportType.UDP)
        print(f"\n[传输] 监听: {transport.info().host}:{transport.info().port}")
        
        # 启动
        lib.start()
        
        # 配置音频（尝试设置，失败也继续）
        try:
            lib.set_snd_dev(-1, -1)  # 使用默认设备
            print("[音频] 已配置默认设备")
        except Exception as e:
            print(f"[警告] 音频配置失败: {e}")
        
        # 创建账户
        acc_cfg = pj.AccountConfig()
        acc_cfg.id = f"sip:{CALLER}@{SERVER}"
        acc_cfg.reg_uri = ""
        acc = lib.create_account(acc_cfg)
        
        print("\n[呼叫] 正在发起...")
        
        # 创建回调并发起呼叫
        call_cb = SafeCallCallback()
        current_call = acc.make_call(sip_uri, cb=call_cb)
        
        print("[等待] 按 Ctrl+C 可中断\n")
        
        # 等待呼叫完成或超时
        start_time = time.time()
        
        while True:
            elapsed = time.time() - start_time
            
            # 安全检查呼叫状态
            try:
                if not current_call or not current_call.is_valid():
                    print("\n[结束] 呼叫已失效")
                    break
                
                with call_cb.lock:
                    state = current_call.info().state
                    if state == pj.CallState.DISCONNECTED:
                        print("\n[结束] 呼叫已断开")
                        break
                        
            except Exception as e:
                print(f"\n[异常] 状态检查失败: {e}")
                break
            
            # 超时检查
            if elapsed >= timeout:
                print(f"\n[超时] 达到 {timeout} 秒，挂断")
                try:
                    if current_call and current_call.is_valid():
                        current_call.hangup()
                except:
                    pass
                break
            
            # 进度提示
            if int(elapsed) % 10 == 0 and elapsed > 0:
                print(f"[进度] {elapsed:.0f}秒...")
            
            time.sleep(1)
        
        # 等待清理
        time.sleep(1)
        
    except KeyboardInterrupt:
        print("\n\n[中断] 用户退出")
        
    except pj.Error as e:
        print(f"\n[错误] PJSUA: {e}")
        
    finally:
        # 安全清理
        print("\n[清理] 正在清理资源...")
        
        if current_call:
            try:
                if current_call.is_valid():
                    state = current_call.info().state
                    if state != pj.CallState.DISCONNECTED:
                        current_call.hangup()
                        time.sleep(0.5)
            except Exception as e:
                print(f"[清理] 挂断异常（忽略）: {e}")
        
        if lib:
            try:
                lib.destroy()
                time.sleep(0.5)
            except Exception as e:
                print(f"[清理] 销毁库异常（忽略）: {e}")
        
        print("[完成] 清理完毕")


def main():
    if len(sys.argv) < 2:
        print("用法: python3 test_call_safe.py <号码> [超时秒数]")
        print("示例: python3 test_call_safe.py 81234567890 30")
        sys.exit(1)
    
    number = sys.argv[1]
    timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    
    make_safe_call(number, timeout)


if __name__ == "__main__":
    main()

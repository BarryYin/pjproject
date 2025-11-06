#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIP拨号测试脚本
SIP服务器配置:
- 主服务器: 34.87.85.184:6030
- 备用服务器: 35.198.204.114:6030
- 前缀: 890471
- 送量格式: 890471+国码+号码
"""

import sys
import time
import pjsua as pj

LOG_LEVEL = 4

class CallCallback(pj.CallCallback):
    """呼叫回调处理"""
    
    def __init__(self, call=None):
        pj.CallCallback.__init__(self, call)
        self.call_connected = False
        
    def on_state(self):
        """呼叫状态变化"""
        info = self.call.info()
        print(f"\n[呼叫状态] {info.remote_uri}")
        print(f"  状态: {info.state_text}")
        print(f"  代码: {info.last_code} ({info.last_reason})")
        
        if info.state == pj.CallState.CONFIRMED:
            self.call_connected = True
            print("  >>> 呼叫已接通!")
            
        elif info.state == pj.CallState.DISCONNECTED:
            print("  >>> 呼叫已结束")
            
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


def make_test_call(destination_number, country_code="234", use_backup=False):
    """
    发起测试呼叫
    
    参数:
        destination_number: 目标号码(不含国码)
        country_code: 国家码,默认234(尼日利亚)
        use_backup: 是否使用备用服务器
    """
    
    # SIP服务器配置
    PRIMARY_SERVER = "34.87.85.184"
    BACKUP_SERVER = "35.198.204.114"
    SIP_PORT = 6030
    PREFIX = "890471"
    CALLER_NUMBER = "63999005001"  # 主叫号码
    
    server = BACKUP_SERVER if use_backup else PRIMARY_SERVER
    
    # 构造完整号码: 前缀+国码+号码
    full_number = f"{PREFIX}{country_code}{destination_number}"
    sip_uri = f"sip:{full_number}@{server}:{SIP_PORT}"
    
    print("=" * 60)
    print("SIP 测试呼叫配置")
    print("=" * 60)
    print(f"服务器: {server}:{SIP_PORT} ({'备用' if use_backup else '主'})")
    print(f"主叫号码: {CALLER_NUMBER}")
    print(f"前缀: {PREFIX}")
    print(f"国码: {country_code}")
    print(f"目标号码: {destination_number}")
    print(f"完整被叫: {full_number}")
    print(f"SIP URI: {sip_uri}")
    print("=" * 60)
    
    lib = None
    current_call = None
    
    try:
        # 创建库实例
        lib = pj.Lib()
        
        # 初始化库
        lib.init(log_cfg=pj.LogConfig(level=LOG_LEVEL, callback=log_cb))
        
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
        acc_cfg.id = f"sip:{CALLER_NUMBER}@{server}:{SIP_PORT}"
        acc_cfg.reg_uri = ""  # 不注册
        
        # 创建账户
        acc = lib.create_account(acc_cfg)
        
        print("\n[准备] 正在发起呼叫...")
        
        # 发起呼叫
        current_call = acc.make_call(sip_uri, cb=CallCallback())
        
        print("\n按 'h' 挂断, 'q' 退出")
        print("-" * 60)
        
        # 等待用户输入
        while True:
            if not current_call or current_call.info().state == pj.CallState.DISCONNECTED:
                print("\n呼叫已结束")
                break
                
            # 非阻塞读取(简单处理)
            time.sleep(1)
            
            # 这里可以添加按键处理
            # 实际使用时建议使用线程或select来处理输入
            
    except pj.Error as e:
        print(f"\n[错误] PJSUA异常: {e}")
        return False
        
    except KeyboardInterrupt:
        print("\n\n[退出] 用户中断")
        
    finally:
        # 清理
        if current_call and current_call.info().state != pj.CallState.DISCONNECTED:
            print("\n[清理] 挂断呼叫...")
            try:
                current_call.hangup()
                time.sleep(1)
            except:
                pass
                
        if lib:
            print("[清理] 销毁库...")
            try:
                lib.destroy()
            except:
                pass
                
    return True


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("PJSIP 呼叫测试工具")
    print("=" * 60 + "\n")
    
    if len(sys.argv) < 2:
        print("用法:")
        print(f"  {sys.argv[0]} <目标号码> [国码] [--backup]")
        print("\n示例:")
        print(f"  {sys.argv[0]} 7032945038              # 拨打尼日利亚号码(默认234)")
        print(f"  {sys.argv[0]} 7032945038 234          # 明确指定尼日利亚国码")
        print(f"  {sys.argv[0]} 7032945038 234 --backup # 使用备用服务器")
        print(f"  {sys.argv[0]} 13800138000 86          # 拨打中国号码")
        print("\n配置信息:")
        print(f"  主叫号码: 63999005001")
        print(f"  被叫格式: 890471 + 国码 + 号码")
        print(f"  示例: 890471 234 7032945038")
        sys.exit(1)
    
    destination = sys.argv[1]
    country_code = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != "--backup" else "234"
    use_backup = "--backup" in sys.argv
    
    make_test_call(destination, country_code, use_backup)


if __name__ == "__main__":
    main()

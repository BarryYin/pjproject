#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIP代理服务器 - 中继转发
架构: Mac客户端 → 8.222.33.80(本服务器) → 147.139.205.88(印尼线路)

功能:
1. 在8.222.33.80上运行
2. 接收Mac端的SIP呼叫
3. 转发到印尼SIP服务器
4. 支持音频RTP流转发
"""

import sys
import time
import pjsua as pj
import threading
import socket

# 配置
CONFIG = {
    # 本地监听配置
    'local_ip': '0.0.0.0',  # 监听所有接口
    'local_port': 5080,      # 监听端口（避免与系统5060冲突）
    
    # 上游SIP服务器（印尼线路）
    'upstream_server': '147.139.205.88',
    'upstream_port': 5060,
    
    # 主叫配置
    'caller_number': '6281479242434',
    'prefix': '13462',
    
    # 日志级别
    'log_level': 3
}

LOG_LEVEL = CONFIG['log_level']

class ProxyAccount(pj.AccountCallback):
    """账户回调"""
    
    def __init__(self, account=None):
        pj.AccountCallback.__init__(self, account)


class ProxyCall(pj.CallCallback):
    """呼叫回调 - 处理呼叫转发"""
    
    def __init__(self, call=None):
        pj.CallCallback.__init__(self, call)
        self.start_time = time.time()
        
    def on_state(self):
        info = self.call.info()
        elapsed = time.time() - self.start_time
        
        print(f"\n[{elapsed:.1f}s] 呼叫状态: {info.state_text}")
        print(f"  远程URI: {info.remote_uri}")
        print(f"  响应码: {info.last_code} ({info.last_reason})")
        
        if info.state == pj.CallState.DISCONNECTED:
            print(f"  呼叫结束 (总时长: {elapsed:.1f}秒)")
            
    def on_media_state(self):
        info = self.call.info()
        if info.media_state == pj.MediaState.ACTIVE:
            # 连接音频
            call_slot = info.conf_slot
            pj.Lib.instance().conf_connect(call_slot, 0)
            pj.Lib.instance().conf_connect(0, call_slot)
            print("  [媒体] 音频流已激活")


def log_cb(level, str_log, len):
    """日志回调"""
    if level <= LOG_LEVEL:
        print(str_log, end='')


class SIPProxyServer:
    """SIP代理服务器"""
    
    def __init__(self):
        self.lib = None
        self.acc = None
        self.transport = None
        
    def start(self):
        """启动代理服务器"""
        print("=" * 70)
        print("SIP 代理服务器 - 印度尼西亚线路中继")
        print("=" * 70)
        print(f"\n架构:")
        print(f"  Mac客户端")
        print(f"    ↓")
        print(f"  本服务器: 8.222.33.80:{CONFIG['local_port']}")
        print(f"    ↓")
        print(f"  印尼线路: {CONFIG['upstream_server']}:{CONFIG['upstream_port']}")
        print(f"\n配置:")
        print(f"  监听地址: {CONFIG['local_ip']}:{CONFIG['local_port']}")
        print(f"  上游服务器: {CONFIG['upstream_server']}:{CONFIG['upstream_port']}")
        print(f"  主叫号码: {CONFIG['caller_number']}")
        print(f"  被叫前缀: {CONFIG['prefix']}")
        print("\n" + "=" * 70)
        
        try:
            # 创建库实例
            self.lib = pj.Lib()
            
            # 配置媒体
            media_cfg = pj.MediaConfig()
            media_cfg.enable_ice = False
            media_cfg.no_vad = True
            media_cfg.ec_tail_len = 200
            media_cfg.clock_rate = 8000
            
            # 初始化
            self.lib.init(
                log_cfg=pj.LogConfig(level=LOG_LEVEL, callback=log_cb),
                media_cfg=media_cfg
            )
            
            # 创建传输 - 监听指定端口
            transport_cfg = pj.TransportConfig(CONFIG['local_port'])
            self.transport = self.lib.create_transport(
                pj.TransportType.UDP,
                transport_cfg
            )
            
            print(f"\n✓ UDP传输已创建")
            print(f"  监听: {self.transport.info().host}:{self.transport.info().port}")
            
            # 启动库
            self.lib.start()
            
            # 配置音频设备（null设备，因为服务器没有音频硬件）
            try:
                self.lib.set_null_snd_dev()
                print("✓ 使用null音频设备（服务器模式）")
            except Exception:
                pass
            
            # 创建账户（不注册，只用于转发）
            acc_cfg = pj.AccountConfig()
            acc_cfg.id = f"sip:{CONFIG['caller_number']}@{CONFIG['upstream_server']}"
            acc_cfg.reg_uri = ""  # 不注册
            
            self.acc = self.lib.create_account(acc_cfg, cb=ProxyAccount())
            
            print("✓ 账户已创建（转发模式）")
            print("\n" + "=" * 70)
            print("代理服务器已启动！")
            print("=" * 70)
            print(f"\nMac客户端配置:")
            print(f"  SIP服务器: 8.222.33.80:{CONFIG['local_port']}")
            print(f"  用户名: {CONFIG['caller_number']}")
            print(f"  拨号格式: {CONFIG['prefix']}<号码>")
            print(f"  示例: {CONFIG['prefix']}82121065486")
            print("\n按 Ctrl+C 停止服务器")
            print("=" * 70 + "\n")
            
            # 保持运行
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n\n正在停止服务器...")
                
        except pj.Error as e:
            print(f"\n✗ PJSUA错误: {e}")
            return False
            
        finally:
            self.stop()
            
        return True
    
    def stop(self):
        """停止代理服务器"""
        if self.lib:
            try:
                print("清理资源...")
                self.lib.destroy()
                self.lib = None
            except Exception:
                pass
        print("服务器已停止")
    
    def make_call(self, destination_number):
        """
        转发呼叫到上游服务器
        
        参数:
            destination_number: 目标号码（包含前缀）
        """
        if not self.acc:
            print("✗ 账户未初始化")
            return None
            
        # 构造上游SIP URI
        full_number = f"{CONFIG['prefix']}{destination_number}"
        sip_uri = f"sip:{full_number}@{CONFIG['upstream_server']}:{CONFIG['upstream_port']}"
        
        print(f"\n转发呼叫:")
        print(f"  目标号码: {full_number}")
        print(f"  上游URI: {sip_uri}")
        
        try:
            call = self.acc.make_call(sip_uri, cb=ProxyCall())
            return call
        except pj.Error as e:
            print(f"✗ 呼叫失败: {e}")
            return None


def main():
    """主函数"""
    if len(sys.argv) > 1:
        print("用法: ./sip_proxy_server.py")
        print("\n启动SIP代理服务器，等待Mac客户端连接")
        print("\n配置说明:")
        print(f"  本地监听端口: {CONFIG['local_port']}")
        print(f"  上游服务器: {CONFIG['upstream_server']}:{CONFIG['upstream_port']}")
        sys.exit(1)
    
    proxy = SIPProxyServer()
    proxy.start()


if __name__ == "__main__":
    main()

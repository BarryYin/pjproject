#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RTP音频桥接器
功能: 监听RTP端口，捕获音频流，转发到WebSocket
原理: 
1. PJSIP在某个UDP端口接收RTP包
2. 我们复制这些包的音频数据
3. 解析RTP头，提取payload（音频数据）
4. 通过WebSocket发送到浏览器
"""

import socket
import struct
import threading
import time

class RTPPacket:
    """RTP包解析器"""
    
    def __init__(self, data):
        """
        RTP包格式:
        0                   1                   2                   3
        0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |V=2|P|X|  CC   |M|     PT      |       sequence number         |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |                           timestamp                           |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |           synchronization source (SSRC) identifier            |
        +=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+
        |                       payload (audio data)                    |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        """
        if len(data) < 12:
            raise ValueError("RTP包太短")
        
        # 解析RTP头（前12字节）
        header = struct.unpack('!BBHII', data[:12])
        
        self.version = (header[0] >> 6) & 0x03
        self.padding = (header[0] >> 5) & 0x01
        self.extension = (header[0] >> 4) & 0x01
        self.cc = header[0] & 0x0F
        
        self.marker = (header[1] >> 7) & 0x01
        self.payload_type = header[1] & 0x7F
        
        self.sequence = header[2]
        self.timestamp = header[3]
        self.ssrc = header[4]
        
        # 计算头部长度
        header_len = 12 + (self.cc * 4)
        
        # 提取payload（音频数据）
        self.payload = data[header_len:]
    
    def __str__(self):
        return (f"RTP[seq={self.sequence}, ts={self.timestamp}, "
                f"pt={self.payload_type}, len={len(self.payload)}]")


class RTPAudioBridge:
    """RTP音频桥接器"""
    
    def __init__(self, listen_port=None):
        """
        参数:
            listen_port: 监听的RTP端口（如果为None，自动从PJSIP获取）
        """
        self.listen_port = listen_port
        self.socket = None
        self.running = False
        self.audio_callback = None
        self.packets_received = 0
        self.last_sequence = -1
        
    def set_audio_callback(self, callback):
        """设置音频数据回调函数"""
        self.audio_callback = callback
    
    def start(self, port):
        """启动RTP监听"""
        if self.running:
            print("[RTP桥接] 已在运行")
            return False
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # 绑定到指定端口
            self.socket.bind(('0.0.0.0', port))
            self.listen_port = port
            self.running = True
            
            print(f"[RTP桥接] ✓ 监听端口: {port}")
            
            # 启动接收线程
            thread = threading.Thread(target=self._receive_loop, daemon=True)
            thread.start()
            
            return True
            
        except Exception as e:
            print(f"[RTP桥接] ✗ 启动失败: {e}")
            return False
    
    def _receive_loop(self):
        """RTP接收循环"""
        print("[RTP桥接] 接收循环已启动")
        
        while self.running:
            try:
                # 接收RTP包
                data, addr = self.socket.recvfrom(2048)
                
                # 解析RTP包
                try:
                    rtp_packet = RTPPacket(data)
                    
                    # 检测丢包
                    if self.last_sequence >= 0:
                        expected = (self.last_sequence + 1) % 65536
                        if rtp_packet.sequence != expected:
                            lost = (rtp_packet.sequence - expected) % 65536
                            if lost < 100:  # 合理范围内的丢包
                                print(f"[RTP桥接] ⚠ 丢包检测: 丢失 {lost} 个包")
                    
                    self.last_sequence = rtp_packet.sequence
                    self.packets_received += 1
                    
                    # 每100个包打印一次统计
                    if self.packets_received % 100 == 0:
                        print(f"[RTP桥接] 已接收 {self.packets_received} 个RTP包")
                    
                    # 调用回调函数，传递音频数据
                    if self.audio_callback:
                        self.audio_callback(rtp_packet.payload)
                        
                except ValueError as e:
                    # 可能不是有效的RTP包
                    pass
                    
            except Exception as e:
                if self.running:
                    print(f"[RTP桥接] 接收错误: {e}")
                break
        
        print("[RTP桥接] 接收循环已停止")
    
    def stop(self):
        """停止RTP监听"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        print("[RTP桥接] 已停止")


def test_rtp_bridge():
    """测试RTP桥接器"""
    
    print("\n" + "="*70)
    print("RTP音频桥接器测试")
    print("="*70 + "\n")
    
    def audio_data_callback(audio_data):
        """接收到音频数据的回调"""
        print(f"收到音频数据: {len(audio_data)} 字节")
        # 这里可以将数据发送到WebSocket
    
    # 创建桥接器
    bridge = RTPAudioBridge()
    bridge.set_audio_callback(audio_data_callback)
    
    # 测试端口（需要从PJSIP获取实际端口）
    test_port = 4000  # 示例端口
    
    print(f"尝试监听RTP端口: {test_port}")
    print("注意: 实际使用时需要从PJSIP获取正确的RTP端口\n")
    
    if bridge.start(test_port):
        print("\n✓ RTP桥接器已启动")
        print("等待RTP包...\n")
        print("按 Ctrl+C 停止\n")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n停止中...")
            bridge.stop()
    else:
        print("\n✗ 启动失败")


if __name__ == "__main__":
    test_rtp_bridge()

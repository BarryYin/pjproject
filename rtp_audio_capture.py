#!/usr/bin/env python3
"""
RTP音频捕获 - 直接监听RTP端口
不依赖PJSUA的限制，直接从网络层抓包
"""

import socket
import struct
import asyncio
import queue

class RTPCapture:
    def __init__(self):
        self.audio_queue = queue.Queue(maxsize=100)
        self.running = False
        
    def parse_rtp_packet(self, data):
        """解析RTP包"""
        if len(data) < 12:
            return None
            
        # RTP头部 (12字节)
        byte0, byte1 = struct.unpack('BB', data[0:2])
        
        version = (byte0 >> 6) & 0x03
        padding = (byte0 >> 5) & 0x01
        extension = (byte0 >> 4) & 0x01
        csrc_count = byte0 & 0x0F
        
        marker = (byte1 >> 7) & 0x01
        payload_type = byte1 & 0x7F
        
        seq_num, timestamp, ssrc = struct.unpack('>HII', data[2:12])
        
        # 计算头部长度
        header_len = 12 + (csrc_count * 4)
        
        if extension:
            if len(data) < header_len + 4:
                return None
            ext_len = struct.unpack('>H', data[header_len+2:header_len+4])[0]
            header_len += 4 + (ext_len * 4)
        
        # 提取音频载荷
        payload = data[header_len:]
        
        if padding and len(payload) > 0:
            padding_len = payload[-1]
            payload = payload[:-padding_len]
        
        return {
            'version': version,
            'payload_type': payload_type,
            'seq_num': seq_num,
            'timestamp': timestamp,
            'ssrc': ssrc,
            'payload': payload
        }
    
    def decode_pcmu(self, data):
        """解码PCMU (G.711 μ-law)"""
        # 简化的μ-law解码
        samples = []
        for byte in data:
            # μ-law解压缩
            sign = 1 if byte & 0x80 else -1
            exponent = (byte >> 4) & 0x07
            mantissa = byte & 0x0F
            
            sample = (((mantissa << 3) + 132) << exponent) - 132
            sample *= sign
            samples.append(sample)
        
        return samples
    
    async def capture_from_port(self, rtp_port):
        """从指定RTP端口捕获音频"""
        print(f"[RTP] 开始监听端口 {rtp_port}")
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', rtp_port))
        sock.settimeout(0.1)
        
        self.running = True
        packet_count = 0
        
        while self.running:
            try:
                data, addr = sock.recvfrom(2048)
                
                # 解析RTP包
                rtp = self.parse_rtp_packet(data)
                if rtp:
                    packet_count += 1
                    
                    # 放入队列
                    if not self.audio_queue.full():
                        self.audio_queue.put(rtp['payload'])
                    
                    if packet_count % 50 == 0:
                        print(f"[RTP] 已捕获 {packet_count} 个音频包")
                        print(f"      序列号: {rtp['seq_num']}, "
                              f"载荷类型: {rtp['payload_type']}, "
                              f"大小: {len(rtp['payload'])} 字节")
            
            except socket.timeout:
                await asyncio.sleep(0.01)
            except Exception as e:
                print(f"[RTP] 错误: {e}")
        
        sock.close()
        print("[RTP] 停止监听")
    
    def stop(self):
        """停止捕获"""
        self.running = False

if __name__ == '__main__':
    # 测试
    capture = RTPCapture()
    
    try:
        # 假设RTP端口是4000
        asyncio.run(capture.capture_from_port(4000))
    except KeyboardInterrupt:
        capture.stop()
        print("\n已停止")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket到SIP的网关
将WebSocket的SIP消息转发到UDP SIP服务器
"""

import asyncio
import websockets
import socket
import json

# 配置
SIP_SERVER = '147.139.205.88'
SIP_PORT = 5060
WS_PORT = 5070

class WebSocketSIPGateway:
    def __init__(self):
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind(('0.0.0.0', 0))  # 绑定随机端口
        self.clients = {}
        
    async def handle_client(self, websocket, path):
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        self.clients[client_id] = websocket
        
        print(f"[网关] 新客户端连接: {client_id}")
        
        try:
            async for message in websocket:
                # 从WebSocket接收SIP消息
                print(f"[WS→UDP] {len(message)} 字节")
                
                # 转发到SIP服务器
                self.udp_socket.sendto(message.encode() if isinstance(message, str) else message, 
                                      (SIP_SERVER, SIP_PORT))
                
        except websockets.exceptions.ConnectionClosed:
            print(f"[网关] 客户端断开: {client_id}")
        finally:
            del self.clients[client_id]
    
    async def udp_listener(self):
        """监听UDP响应"""
        loop = asyncio.get_event_loop()
        
        while True:
            # 从SIP服务器接收响应
            data, addr = await loop.run_in_executor(None, self.udp_socket.recvfrom, 2048)
            
            print(f"[UDP→WS] {len(data)} 字节 from {addr}")
            
            # 转发给所有WebSocket客户端
            for client_id, ws in list(self.clients.items()):
                try:
                    await ws.send(data.decode())
                except:
                    pass
    
    async def start(self):
        print(f"[网关] 启动WebSocket服务器: ws://0.0.0.0:{WS_PORT}")
        print(f"[网关] SIP服务器: {SIP_SERVER}:{SIP_PORT}")
        
        # 启动WebSocket服务器
        ws_server = await websockets.serve(self.handle_client, '0.0.0.0', WS_PORT)
        
        # 启动UDP监听
        await self.udp_listener()

if __name__ == '__main__':
    gateway = WebSocketSIPGateway()
    
    try:
        asyncio.run(gateway.start())
    except KeyboardInterrupt:
        print("\n[网关] 已停止")

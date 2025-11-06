# WebSocket 连接问题说明

## 问题现象

```
拨号失败: Cannot read properties of null (reading 'call')
```

## 根本原因

**该SIP服务器 (147.139.205.88:5060) 不支持 WebSocket 协议！**

传统的SIP服务器使用 **UDP/TCP** 协议，而网页浏览器只能使用 **WebSocket (ws://)** 或 **WebSocket Secure (wss://)** 协议。

## 解决方案

### ✅ 方案1：使用Python脚本（推荐）

Python脚本使用传统的UDP协议，完全兼容：

```bash
cd /home/henry/pjproject
./sip_test_call_indonesia.py 82121065486
```

**优点**：
- ✓ 支持UDP/TCP协议
- ✓ 完全兼容传统SIP服务器
- ✓ 已经过测试，可以正常拨号

**缺点**：
- ✗ 需要在服务器上运行
- ✗ 无法直接在Mac上听到声音（服务器没有音频设备）

### ⚙️ 方案2：配置WebSocket代理

如果必须使用Web客户端，需要在SIP服务器和浏览器之间架设一个 **WebSocket-to-UDP 代理**。

常用工具：
1. **Kamailio** - 开源SIP服务器，支持WebSocket
2. **Asterisk** - 带WebSocket支持
3. **rtpengine** - WebRTC网关

这需要在服务器端配置，较为复杂。

### 💡 方案3：咨询服务商

联系SIP线路提供商，询问：
1. 是否支持WebSocket协议？
2. WebSocket端口是多少？（可能不是5060）
3. 是否需要使用WSS（加密）？

## 技术说明

### 协议对比

| 协议类型 | 端口 | 用途 | 浏览器支持 |
|---------|------|------|-----------|
| SIP over UDP | 5060 | 传统SIP | ✗ 不支持 |
| SIP over TCP | 5060 | 传统SIP | ✗ 不支持 |
| SIP over WebSocket | 自定义 | 网页SIP | ✓ 支持 |
| SIP over WSS | 自定义 | 加密网页SIP | ✓ 支持 |

### WebSocket检测

当前配置尝试连接：
```
ws://147.139.205.88:5060
```

如果5秒后仍未连接成功，说明该服务器不支持WebSocket。

## 建议

**对于印度尼西亚这条线路：使用 Python 脚本版本**

Web版客户端更适合：
- 有WebSocket支持的SIP服务器
- 需要在浏览器中使用的场景
- 云呼叫中心等Web应用

如果只是测试线路连通性和音频质量，Python脚本版本更合适。

## 测试步骤

1. **先用Python脚本测试连通性**：
   ```bash
   ./sip_test_call_indonesia.py 82121065486
   ```

2. **如果需要听到声音**：
   - 在本地Mac上安装pjsua
   - 或使用支持WebSocket的SIP服务器

3. **确认Web版是否可用**：
   - 打开浏览器开发者工具（F12）
   - 查看Console标签
   - 如果看到WebSocket连接错误，说明不支持

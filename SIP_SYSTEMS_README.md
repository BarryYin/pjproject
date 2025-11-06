# SIP 通信系统集合

本项目包含**四个**完整的SIP通信系统，适用于不同场景和环境。

## 📦 系统列表

### 1. WebSocket双向通话系统 ⭐⭐ **最新**

**文件**: `sip_websocket_call_system.py`

**特点**:
- ✅ **服务器端SIP + 浏览器音频** - 最佳架构
- ✅ WebSocket实时音频流
- ✅ 无需服务器音频设备
- ✅ Web Audio API接入本地麦克风/扬声器
- ✅ 跨平台（任何现代浏览器）
- ✅ 完整的双向通话架构

**使用场景**:
- 远程服务器部署（无音频设备）
- Web应用集成
- 云端呼叫中心
- 分布式通话系统

**快速启动**:
```bash
python3 sip_websocket_call_system.py
# 浏览器访问: http://localhost:8089
```

**文档**: `WEBSOCKET_CALL_GUIDE.md`

**Web界面**: http://localhost:8089

---

### 2. 双向实时通话系统

**文件**: `sip_live_call_system.py`

**特点**:
- ✅ **真正的双向实时通话** - 你和对方可以互相听到声音
- ✅ 支持麦克风输入和扬声器输出
- ✅ Web控制界面 + HTTP API
- ✅ 静音、录音、挂断等完整功能
- ✅ 自动音频设备检测

**使用场景**:
- 真人对话、客服通话
- 远程会议、电话沟通
- 需要双向交流的场景

**快速启动**:
```bash
./start_live_call.sh
# 或
python3 sip_live_call_system.py
```

**文档**:
- 📘 快速开始: `LIVE_CALL_QUICK_START.md`
- 📗 详细文档: `LIVE_CALL_GUIDE.md`

**Web界面**: http://localhost:8089

---

### 3. IVR自动语音播报系统

**文件**: `sip_ivr_system.py`

**特点**:
- ✅ 自动拨号
- ✅ 播放预录音频文件
- ✅ 录制通话内容
- ✅ HTTP API控制
- ✅ Web管理界面

**使用场景**:
- 自动语音通知、播报
- 电话营销、语音广播
- 批量通知、提醒服务

**快速启动**:
```bash
python3 sip_ivr_system.py
```

**文档**: `IVR_GUIDE.md`

**Web界面**: http://localhost:8088

---

### 4. 简单拨号测试工具

**文件**: `sip_test_call_indonesia.py`

**特点**:
- ✅ 命令行直接拨号
- ✅ 支持按键控制（挂断、静音等）
- ✅ 详细状态显示
- ✅ 无需Web界面

**使用场景**:
- 快速测试SIP连接
- 命令行环境使用
- 调试和测试

**快速启动**:
```bash
python3 sip_test_call_indonesia.py 82121065486
```

---

## 🆚 系统对比

| 功能 | WebSocket系统 | 直接音频系统 | IVR系统 | 测试工具 |
|------|--------------|-------------|---------|---------|
| **双向实时通话** | ✅ | ✅ | ❌ | ✅ |
| **服务器无需音频设备** | ✅ | ❌ | ✅ | ❌ |
| **浏览器接入** | ✅ | ❌ | ❌ | ❌ |
| **Web界面** | ✅ | ✅ | ✅ | ❌ |
| **HTTP API** | ✅ | ✅ | ✅ | ❌ |
| **播放录音文件** | ❌ | ❌ | ✅ | ❌ |
| **录音功能** | 计划中 | ✅ | ✅ | ❌ |
| **部署灵活性** | ⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐ |
| **使用复杂度** | 简单 | 简单 | 中等 | 最简单 |

## 🎯 如何选择

### 选择WebSocket系统，如果你需要：⭐ **推荐**
- 在**远程服务器**上部署（无音频设备）
- **浏览器端**接入通话
- 最大的部署灵活性
- 跨平台支持

### 选择直接音频系统，如果你需要：
- 在**本地环境**运行（有音频设备）
- 最简单的设置
- 不需要浏览器

### 选择IVR系统，如果你需要：
- **播放预录音频**给对方听
- 自动语音通知、播报
- 批量拨打电话播放录音
- 不需要双向对话

### 选择测试工具，如果你需要：
- 快速测试SIP服务器连接
- 命令行环境
- 不需要Web界面
- 简单的拨号测试

## 📋 SIP配置（印度尼西亚线路）

所有系统使用相同的SIP配置：

```
服务器: 147.139.205.88:5060
主叫号码: 6281479242434
被叫前缀: 13462
拨打格式: 13462 + 目标号码
```

示例：
- 输入号码: `82121065486`
- 实际拨打: `1346282121065486`

## 📂 文件结构

```
/home/henry/pjproject/
├── sip_websocket_call_system.py # WebSocket系统 ⭐⭐ 最新
├── WEBSOCKET_CALL_GUIDE.md      # WebSocket详细文档
│
├── sip_live_call_system.py      # 直接音频系统
├── start_live_call.sh            # 直接音频启动脚本
├── LIVE_CALL_QUICK_START.md     # 直接音频快速开始
├── LIVE_CALL_GUIDE.md            # 直接音频详细文档
│
├── sip_ivr_system.py             # IVR系统
├── IVR_GUIDE.md                  # IVR文档
│
├── sip_test_call_indonesia.py   # 测试工具
│
├── recordings/                   # 录音保存目录
├── audio_files/                  # IVR音频文件目录
│
└── SIP_SYSTEMS_README.md         # 本文件
```

## 🚀 快速开始示例

### WebSocket系统 ⭐ 推荐

```bash
# 启动系统
python3 sip_websocket_call_system.py

# 浏览器访问
# http://localhost:8089
# 允许麦克风权限，即可拨号
```

### 直接音频系统

```bash
# 启动系统
./start_live_call.sh

# 使用API拨号
curl -X POST http://localhost:8089/api/call \
  -H "Content-Type: application/json" \
  -d '{"phone_number":"82121065486"}'

# 或使用Web界面
# 浏览器打开: http://localhost:8089
```

### IVR系统

```bash
# 启动系统
python3 sip_ivr_system.py

# 使用API拨号并播放录音
curl -X POST http://localhost:8088/api/call \
  -H "Content-Type: application/json" \
  -d '{"phone_number":"82121065486"}'

# 或使用Web界面
# 浏览器打开: http://localhost:8088
```

### 测试工具

```bash
# 直接拨号
python3 sip_test_call_indonesia.py 82121065486

# 设置超时时间（秒）
python3 sip_test_call_indonesia.py 82121065486 30
```

## ⚠️ 重要提示

### 音频设备

所有系统都支持音频设备配置：

1. **本地环境**（有麦克风和扬声器）：
   - 双向通话系统：完全支持，自动检测设备
   - IVR系统：不使用音频设备（播放录音）
   - 测试工具：完全支持

2. **服务器环境**（无音频设备）：
   - 双向通话系统：会显示警告，可运行但无声音
   - IVR系统：正常工作（不需要音频设备）
   - 测试工具：会显示警告，可运行但无声音

### 端口使用

- 双向通话系统：`8089`
- IVR系统：`8088`
- 测试工具：无需端口

确保端口未被占用。

## 📞 测试建议

1. **首次测试**：使用测试工具快速验证SIP连接
   ```bash
   python3 sip_test_call_indonesia.py 82121065486
   ```

2. **IVR测试**：准备好音频文件后使用IVR系统
   ```bash
   # 放置音频文件到 audio_files/welcome.wav
   python3 sip_ivr_system.py
   ```

3. **实时通话**：在本地环境使用双向通话系统
   ```bash
   ./start_live_call.sh
   ```

## 🐛 故障排查

### 问题：无法拨号

**解决**：
1. 检查SIP服务器是否可达
2. 确认号码格式正确
3. 查看系统日志

### 问题：听不到声音（双向通话系统）

**解决**：
1. 确认在本地环境运行（不是远程服务器）
2. 检查音频设备是否正常
3. 查看系统日志中的音频设备检测结果

### 问题：IVR不播放录音

**解决**：
1. 确认音频文件存在于 `audio_files/` 目录
2. 检查文件格式（需要WAV格式）
3. 查看日志中的播放状态

### 问题：API无响应

**解决**：
1. 确认系统已启动
2. 检查端口是否被占用
3. 尝试重启系统

## 📚 更多文档

- **WebSocket系统** ⭐:
  - `WEBSOCKET_CALL_GUIDE.md` - 完整指南

- **直接音频系统**:
  - `LIVE_CALL_QUICK_START.md` - 快速开始
  - `LIVE_CALL_GUIDE.md` - 详细指南

- **IVR系统**:
  - `IVR_GUIDE.md` - 使用指南

- **项目文档**:
  - `README.md` - PJSIP项目主文档
  - `QUICK_START.md` - PJSIP快速开始

## 🤝 技术支持

- PJSIP官网: https://www.pjsip.org/
- Python PJSUA文档: https://www.pjsip.org/python/pjsua.htm

---

## 🌟 推荐选择

### 场景1: 服务器部署（推荐）

**使用 WebSocket系统** ⭐⭐
- 服务器无需音频设备
- 浏览器接入，跨平台
- 最灵活的部署方案

### 场景2: 本地使用

**使用 直接音频系统**
- 有真实音频设备
- 最简单的配置
- 即插即用

### 场景3: 自动语音播报

**使用 IVR系统**
- 播放预录音频
- 批量通知
- 不需要双向对话

---

**提示**: 对于大多数场景，推荐使用 **WebSocket系统**！它结合了服务器端SIP处理和浏览器音频接入的优势。

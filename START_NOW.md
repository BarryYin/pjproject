# 🚀 立即启动 - 端口已更改为8090

## ✅ 已解决端口冲突

**端口已从 8089 改为 8090**

---

## 🎯 现在立即启动

### 方法1: 使用启动脚本（推荐）

```bash
cd /home/henry/pjproject
./start_ai_8090.sh
```

### 方法2: 直接启动

```bash
cd /home/henry/pjproject
export OPENAI_API_KEY='<OPENAI_API_KEY>'
python3 sip_ai_conversation.py
```

---

## 🌐 访问地址

启动成功后访问：

```
http://localhost:8090
```

或从外部访问：
```
http://你的服务器IP:8090
```

---

## 📊 端口使用说明

| 端口 | 用途 | 状态 |
|------|------|------|
| 8089 | 被其他服务占用 | ❌ 已避开 |
| 8090 | AI对话系统 | ✅ 当前使用 |
| 8088 | 双向语音系统 | 独立运行 |

---

## ⏱️ 首次启动提示

**首次启动需要2-3分钟**，系统会下载Whisper模型：

```
[ASR] 正在加载 faster-whisper 模型...
  模型: base
  设备: cpu
  计算类型: int8
  ✓ ASR模型加载成功     ← 看到这个后才能访问
✓ API服务器: http://localhost:8090
```

---

## ✅ 启动成功标志

看到以下输出说明启动成功：

```
✓ 传输创建: xxx.xxx.xxx.xxx:xxxxx
✓ 音频设备: null设备 (服务器模式)
✓ 账户已创建
✓ 系统启动成功!
✓ API服务器: http://localhost:8090

使用说明:
  1. 访问: http://localhost:8090    ← 注意是8090!
  2. 输入号码并点击'开始AI对话'
  3. 系统会自动识别和回复
```

---

## 🔧 如果还有问题

### 端口仍被占用？

检查8090端口：
```bash
netstat -tln | grep 8090
```

如果被占用，可以再改为其他端口：
```bash
# 编辑 sip_ai_conversation.py
# 将 'api_port': 8090 改为 8091 或其他
```

### 系统无响应？

等待2-3分钟（首次下载模型），或查看运行窗口的输出日志。

---

## 💡 快速测试

启动后测试API：
```bash
curl http://localhost:8090/api/status
```

应该返回：
```json
{"success": true, "has_active_call": false, ...}
```

---

**现在执行**: `./start_ai_8090.sh` 🚀

访问: **http://localhost:8090**

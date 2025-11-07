# 简单使用指南 - 无需前端

## 🎯 直接使用后端

### 方法1：命令行交互菜单（推荐）

```bash
cd /home/henry/pjproject
./use_backend_directly.sh
```

**会显示菜单**：
```
================================
  操作菜单
================================
1. 发起AI对话呼叫
2. 挂断当前呼叫
3. 查看系统状态
4. 添加音频到队列
5. 立即播放音频
6. 退出

选择操作 (1-6):
```

输入数字，按提示操作即可。

---

### 方法2：直接用curl命令

#### 发起呼叫
```bash
curl -X POST http://localhost:8090/api/call \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "82121065486"}'
```

#### 挂断呼叫
```bash
curl -X POST http://localhost:8090/api/hangup
```

#### 查看状态
```bash
curl -X POST http://localhost:8090/api/status
```

#### 添加音频到队列
```bash
curl -X POST http://localhost:8090/api/add_audio \
  -H "Content-Type: application/json" \
  -d '{"filename": "welcome.wav"}'
```

#### 立即播放音频
```bash
curl -X POST http://localhost:8090/api/play_now \
  -H "Content-Type: application/json" \
  -d '{"filename": "urgent.wav"}'
```

---

### 方法3：Python脚本

创建 `test_call.py`：
```python
import requests

API = "http://localhost:8090"

# 发起呼叫
response = requests.post(f"{API}/api/call", 
                        json={"phone_number": "82121065486"})
print(response.json())

# 查看状态
response = requests.post(f"{API}/api/status")
print(response.json())
```

运行：
```bash
python3 test_call.py
```

---

## 🚀 完整流程

### 1. 确保后端运行

```bash
# 检查后端
ps aux | grep sip_ai_conversation

# 如果没运行，启动它
cd /home/henry/pjproject
export OPENAI_API_KEY='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'
nohup python3 sip_ai_conversation.py > /tmp/ai_backend.log 2>&1 &
```

### 2. 使用命令行菜单

```bash
./use_backend_directly.sh
```

### 3. 或直接用curl

```bash
# 发起呼叫
curl -X POST http://localhost:8090/api/call \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "82121065486"}'
```

---

## 📊 示例对话

```bash
$ ./use_backend_directly.sh

========================================
  AI对话系统 - 命令行控制
========================================

检查后端状态...
✓ 后端运行正常

================================
  操作菜单
================================
1. 发起AI对话呼叫
2. 挂断当前呼叫
3. 查看系统状态
4. 添加音频到队列
5. 立即播放音频
6. 退出

选择操作 (1-6): 1

输入电话号码: 82121065486
正在发起呼叫...
响应: {"success": true, "message": "AI对话已启动"}

选择操作 (1-6): 3

系统状态:
{
    "success": true,
    "has_active_call": true,
    "call_connected": true,
    "ai_ready": true
}

选择操作 (1-6): 6

退出
```

---

## 🎉 优点

✅ **无需前端** - 纯命令行操作  
✅ **简单直接** - 一个脚本搞定  
✅ **功能完整** - 所有API都能用  
✅ **易于集成** - 可以写到其他脚本中  

---

## 💡 后端日志

查看实时日志：
```bash
tail -f /tmp/ai_backend.log
```

---

## 🔧 后端管理

### 启动后端
```bash
cd /home/henry/pjproject
nohup python3 sip_ai_conversation.py > /tmp/ai_backend.log 2>&1 &
```

### 停止后端
```bash
pkill -f sip_ai_conversation.py
```

### 检查后端
```bash
ps aux | grep sip_ai_conversation
curl -s http://localhost:8090/api/status
```

---

## ✅ 总结

**不需要前端！**

使用命令行菜单：
```bash
./use_backend_directly.sh
```

或直接用curl调用API即可！

简单、直接、有效！🎉

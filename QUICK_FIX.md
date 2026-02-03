# 🔧 快速修复指南

## 问题：端口8089已被占用

### 原因
系统已经在运行，或者上次启动时异常退出导致端口未释放。

---

## ✅ 解决方案（选一个）

### 方案1: 智能启动（推荐）⭐
自动检测并解决所有问题

```bash
cd /home/henry/pjproject
./smart_start.sh
```

**功能**:
- ✅ 自动检测系统是否运行
- ✅ 如运行正常，询问是否重启
- ✅ 如运行异常，自动清理并重启
- ✅ 检查所有依赖和配置

---

### 方案2: 一键修复
强制停止并重新启动

```bash
cd /home/henry/pjproject
./fix_and_start.sh
```

**功能**:
- 停止所有旧进程
- 清理端口
- 重新启动系统

---

### 方案3: 手动操作
完全控制每一步

```bash
# 1. 停止旧进程
pkill -f sip_ai_conversation.py

# 2. 等待端口释放
sleep 3

# 3. 重新启动
cd /home/henry/pjproject
export OPENAI_API_KEY='<OPENAI_API_KEY>'
python3 sip_ai_conversation.py
```

---

### 方案4: 如果系统正常运行
直接访问已运行的实例

```bash
# 检查状态
./check_ai_status.sh

# 如果显示"✓ Web服务响应正常"，直接访问:
http://localhost:8089
```

---

## 🔍 诊断命令

### 检查系统状态
```bash
./check_ai_status.sh
```

### 查看运行进程
```bash
ps aux | grep sip_ai_conversation.py
```

### 查看端口占用
```bash
netstat -tlnp | grep 8089
# 或
ss -tlnp | grep 8089
```

### 查看端口详情
```bash
sudo lsof -i :8089
```

---

## 🐛 常见错误

### 错误1: Address already in use
**原因**: 端口被占用  
**解决**: 使用 `./smart_start.sh` 或 `./fix_and_start.sh`

### 错误2: 系统启动但无法访问
**原因**: 正在下载Whisper模型（首次启动）  
**解决**: 等待2-3分钟，模型下载完成后自动可用

### 错误3: OPENAI_API_KEY未设置
**原因**: 环境变量未配置  
**解决**: 
```bash
export OPENAI_API_KEY='your-key'
# 或运行
./smart_start.sh  # 会自动设置
```

---

## 📊 启动脚本对比

| 脚本 | 功能 | 推荐场景 |
|------|------|---------|
| **smart_start.sh** | 智能检测+自动修复 | ⭐ 日常使用 |
| **fix_and_start.sh** | 强制清理+重启 | 系统异常 |
| **quick_start_ai_conversation.sh** | 基础启动 | 简单启动 |
| **restart_ai_system.sh** | 重启脚本 | 手动重启 |

---

## ✅ 推荐流程

### 首次使用
```bash
1. ./install_ai_dependencies.sh  # 安装依赖（只需一次）
2. ./smart_start.sh              # 智能启动
```

### 日常使用
```bash
./smart_start.sh                 # 每次都用这个
```

### 遇到问题
```bash
1. ./check_ai_status.sh          # 先检查状态
2. ./fix_and_start.sh            # 如有问题，修复启动
```

---

## 🎯 启动后验证

启动成功后，会看到：
```
✓ 传输创建: xxx.xxx.xxx.xxx:xxxxx
✓ 音频设备: null设备 (服务器模式)
✓ 账户已创建
✓ API服务器: http://localhost:8089

使用说明:
  1. 访问: http://localhost:8089
  ...
```

然后访问：**http://localhost:8089**

如果看到AI对话控制面板，说明启动成功！🎉

---

## 💡 终极解决方案

如果所有方法都不行：

```bash
# 1. 彻底清理
pkill -9 -f sip_ai_conversation.py
pkill -9 -f python3

# 2. 检查端口
sudo lsof -i :8089
# 记下PID，然后:
sudo kill -9 <PID>

# 3. 重新启动
./smart_start.sh
```

---

**现在执行**: `./smart_start.sh` 🚀

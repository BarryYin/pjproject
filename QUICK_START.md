# 快速开始指南

## ✅ 编译完成!

PJSIP核心库和Python绑定已成功编译安装。

## 测试呼叫配置

### 服务器信息
- **主服务器**: 34.87.85.184:6030
- **备用服务器**: 35.198.204.114:6030
- **主叫号码**: 63999005001
- **前缀**: 890471
- **被叫格式**: 890471 + 国码 + 号码

### 示例: 拨打尼日利亚号码
```bash
# 拨打号码: 7032945038
# 完整被叫: 890471 234 7032945038 = 8904712347032945038
python3 sip_test_call.py 7032945038
```

## 运行测试

### 基本用法

```bash
cd /home/henry/pjproject

# 1. 拨打尼日利亚号码(默认国码234)
python3 sip_test_call.py 7032945038

# 2. 明确指定国码
python3 sip_test_call.py 7032945038 234

# 3. 使用备用服务器
python3 sip_test_call.py 7032945038 234 --backup

# 4. 拨打中国号码
python3 sip_test_call.py 13800138000 86

# 5. 拨打美国号码
python3 sip_test_call.py 2025551234 1
```

### 预期输出

```
============================================================
SIP 测试呼叫配置
============================================================
服务器: 34.87.85.184:6030 (主)
主叫号码: 63999005001
前缀: 890471
国码: 234
目标号码: 7032945038
完整被叫: 8904712347032945038
SIP URI: sip:8904712347032945038@34.87.85.184:6030
============================================================

[传输] 本地监听: 0.0.0.0:xxxxx

[准备] 正在发起呼叫...

[呼叫状态] sip:8904712347032945038@34.87.85.184:6030
  状态: CALLING
  代码: 0 ()

[呼叫状态] sip:8904712347032945038@34.87.85.184:6030
  状态: Early
  代码: 180 (Ringing)
  
... (等待接听或超时)
```

## 文件说明

1. **sip_test_call.py** - 主测试脚本
   - 配置了双服务器支持
   - 主叫号码: 63999005001
   - 自动拼接被叫格式

2. **BUILD_PYTHON.md** - 详细编译文档
   - 包含完整编译步骤
   - 常见问题排查
   - 依赖安装说明

## 测试要点

### 检查连接
1. 确认能否连接到SIP服务器(34.87.85.184:6030)
2. 观察INVITE请求是否发出
3. 查看服务器响应代码(180/200/486等)

### 调整日志级别
修改脚本中的 `LOG_LEVEL`:
```python
LOG_LEVEL = 5  # 更详细的日志(0-5)
```

### 呼叫超时
脚本会持续运行直到:
- 对方接听
- 对方拒绝
- 超时
- 用户按Ctrl+C中断

## 故障排查

### 1. 无响应
- 检查网络连接
- 确认服务器IP和端口
- 查看防火墙设置

### 2. 403/407错误
- 可能需要SIP认证
- 联系服务提供商确认是否需要用户名/密码

### 3. 号码格式错误
- 确认完整被叫格式: 890471 + 国码 + 号码
- 示例: 8904712347032945038

## 高级配置

### 添加SIP认证
如果需要认证,修改脚本中的账户配置:
```python
acc_cfg = pj.AccountConfig()
acc_cfg.id = f"sip:{CALLER_NUMBER}@{server}:{SIP_PORT}"
acc_cfg.reg_uri = f"sip:{server}:{SIP_PORT}"  # 启用注册

# 添加认证
acc_cfg.cred_count = 1
acc_cfg.cred_info.append(
    pj.AuthCred("*", "username", "password")
)
```

### 自定义呼叫超时
```python
# 在发起呼叫后添加超时控制
import time
start_time = time.time()
timeout_seconds = 30

while True:
    if time.time() - start_time > timeout_seconds:
        print("呼叫超时")
        current_call.hangup()
        break
    time.sleep(1)
```

## 重新编译(如需)

```bash
cd /home/henry/pjproject

# 清理
make clean

# 重新编译(使用-fPIC)
CFLAGS="-fPIC" ./configure
make dep
make -j$(nproc)

# 重新安装Python绑定
cd pjsip-apps/src/python
python3 setup.py install --user --force
```

## 技术支持

如遇到问题:
1. 查看 `BUILD_PYTHON.md` 详细文档
2. 检查PJSIP日志输出
3. 确认SIP服务器配置
4. 联系SIP服务提供商确认账号状态

---

**祝测试顺利! 🚀**

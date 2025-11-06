# PJSIP Python 绑定编译指南

## 快速开始

### 1. 编译 PJSIP 核心库

```bash
cd /home/henry/pjproject

# 配置(使用默认设置)
./configure

# 编译主库
make dep
make

# 这会编译所有C库文件
```

### 2. 编译并安装 Python 绑定

```bash
cd pjsip-apps/src/python

# 编译并安装(推荐使用用户安装)
python3 setup.py install --user

# 或者开发模式安装(代码修改立即生效)
python3 setup.py develop --user

# 或者系统级安装(需要sudo)
# sudo python3 setup.py install
```

### 3. 验证安装

```bash
# 测试导入
python3 -c "import pjsua; print('PJSUA version:', pjsua.version())"

# 如果成功会显示版本信息
```

## 常见问题排查

### 问题1: 找不到头文件或库文件

**错误信息:**
```
fatal error: pjsua-lib/pjsua.h: No such file or directory
```

**解决方法:**
```bash
# 确保先编译主库
cd /home/henry/pjproject
make clean
./configure
make dep && make
```

### 问题2: Python.h 找不到

**错误信息:**
```
fatal error: Python.h: No such file or directory
```

**解决方法:**
```bash
# Ubuntu/Debian
sudo apt-get install python3-dev

# CentOS/RHEL
sudo yum install python3-devel
```

### 问题3: 编译成功但导入失败

**错误信息:**
```
ImportError: cannot import name '_pjsua'
```

**解决方法:**
```bash
# 检查安装路径
python3 -c "import sys; print('\n'.join(sys.path))"

# 添加到PYTHONPATH
export PYTHONPATH=/home/henry/pjproject/pjsip-apps/src/python:$PYTHONPATH

# 或重新安装
cd /home/henry/pjproject/pjsip-apps/src/python
python3 setup.py install --user --force
```

## 完整编译命令(一键执行)

```bash
#!/bin/bash
# 完整编译脚本

set -e  # 遇到错误停止

cd /home/henry/pjproject

echo "步骤 1/4: 配置 PJSIP..."
./configure

echo "步骤 2/4: 生成依赖..."
make dep

echo "步骤 3/4: 编译核心库..."
make

echo "步骤 4/4: 编译Python绑定..."
cd pjsip-apps/src/python
python3 setup.py install --user

echo "完成! 验证安装..."
python3 -c "import pjsua; print('✓ PJSUA 安装成功! 版本:', pjsua.version())"
```

保存为 `build_all.sh` 并执行:
```bash
chmod +x build_all.sh
./build_all.sh
```

## 运行测试脚本

编译完成后:

```bash
# 回到项目根目录
cd /home/henry/pjproject

# 运行测试呼叫(拨打尼日利亚号码)
python3 sip_test_call.py 7032945038

# 使用备用服务器
python3 sip_test_call.py 7032945038 234 --backup

# 拨打其他国家号码
python3 sip_test_call.py 13800138000 86  # 中国
```

## 预期输出

成功运行时会看到:
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
  ...
```

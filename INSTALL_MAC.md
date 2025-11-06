# 在Mac上安装和运行SIP客户端

## 🎯 目标

在你的Mac上直接运行SIP客户端，连接到印尼线路 (147.139.205.88:5060)，这样就能听到声音了！

---

## 方案1：使用Python + PJSUA（推荐）

### 步骤1：安装PJSIP

在Mac终端运行：

```bash
# 使用Homebrew安装
brew install pjsip

# 或者通过pip安装Python绑定
pip3 install pjsua
```

如果没有Homebrew，先安装：
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 步骤2：下载脚本到Mac

从服务器复制脚本到Mac：

```bash
# 在Mac上执行
scp henry@8.222.33.80:/home/henry/pjproject/sip_test_call_indonesia.py ~/Desktop/
```

或者手动创建文件（见下方完整代码）

### 步骤3：运行测试

```bash
cd ~/Desktop
python3 sip_test_call_indonesia.py 82121065486
```

**优点**：
- ✓ Mac有真实音频设备，能听到声音
- ✓ 直接连接到147.139.205.88，无需中转
- ✓ 使用UDP协议，完全兼容

---

## 方案2：使用桌面SIP客户端（最简单）

不需要编程，直接用现成的软件！

### 推荐客户端

#### A. Telephone（Mac免费）

1. **下载安装**：
   ```bash
   brew install --cask telephone
   ```
   或从官网：https://www.64characters.com/telephone/

2. **配置**：
   - 打开 Telephone
   - Account → Add Account
   - **不需要注册**，直接配置：
     - SIP Server: `147.139.205.88:5060`
     - Username: `6281479242434` (主叫号码)
     - 不填密码（如果需要认证再填）
     - 取消勾选 "Register"

3. **拨号**：
   - 在拨号盘输入：`1346282121065486`
   - 点击拨号

#### B. Linphone（跨平台，免费）

1. **下载**：https://www.linphone.org/releases/macosx/app/

2. **配置**：
   - 打开Linphone
   - Settings → SIP Accounts → Add
   - Use SIP address: `sip:6281479242434@147.139.205.88`
   - Transport: UDP
   - Port: 5060
   - Disable register

3. **拨号**：
   - 输入：`sip:1346282121065486@147.139.205.88`

#### C. Zoiper（功能强大）

1. **下载**：https://www.zoiper.com/en/voip-softphone/download/zoiper5

2. **配置类似**，更多高级选项

---

## 方案3：使用SIP URI直接拨号

某些客户端支持直接拨打SIP URI，无需配置账户：

```
sip:1346282121065486@147.139.205.88:5060
```

在支持的客户端（如Linphone）中直接输入这个URI拨号。

---

## 方案4：使用Asterisk/FreeSWITCH（高级）

如果需要更复杂的功能（转接、录音等），可以在Mac或服务器上搭建Asterisk。

---

## 🔧 故障排除

### PJSUA安装失败

如果 `pip3 install pjsua` 失败，尝试：

```bash
# 方法1：从源码编译
git clone https://github.com/pjsip/pjproject.git
cd pjproject
./configure
make dep && make
cd pjsip-apps/src/python
python3 setup.py install

# 方法2：使用conda
conda install -c conda-forge pjsua
```

### 防火墙问题

确保Mac防火墙允许UDP 5060端口：
```bash
# 检查防火墙状态
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate

# 允许Python访问网络（如果需要）
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /usr/local/bin/python3
```

### 音频设备问题

确保系统音量未静音：
- 系统偏好设置 → 声音
- 检查输入/输出设备
- 测试麦克风和扬声器

---

## 📝 完整Python脚本（Mac版）

如果从服务器复制不方便，可以直接在Mac上创建这个文件：

```bash
nano ~/Desktop/sip_call_indonesia.py
```

粘贴脚本内容（与服务器版本相同，但Mac有音频设备，会正常工作）

保存后运行：
```bash
chmod +x ~/Desktop/sip_call_indonesia.py
python3 ~/Desktop/sip_call_indonesia.py 82121065486
```

---

## 🎯 推荐方案

**对于你的需求，我推荐：**

### 🥇 第一选择：Telephone（Mac）
- 最简单，图形界面
- 免费，专为Mac设计
- 3分钟搞定

### 🥈 第二选择：Python脚本
- 可以自定义功能
- 适合批量测试
- 可以集成到其他系统

### 🥉 第三选择：Linphone
- 跨平台，功能强大
- 支持视频通话
- 开源免费

---

## 💡 快速开始（3步）

```bash
# 1. 安装Telephone
brew install --cask telephone

# 2. 打开配置
# - Server: 147.139.205.88:5060
# - Username: 6281479242434
# - 取消勾选Register

# 3. 拨号测试
# 输入: 1346282121065486
```

完成！现在你的Mac就是一个SIP电话了 📞

---

需要我帮你选择哪个方案？或者有其他问题？

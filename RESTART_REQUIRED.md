# ⚠️ 重要：需要重启程序

## 问题

你看到的错误：
```
[错误] 'OptimizedNLSASREngine' object has no attribute 'max_errors'
```

## 原因

✅ **代码已经修复** - 文件中的代码是正确的
❌ **但你的程序还在运行旧版本** - Python进程在启动时加载代码，不会自动重新加载

## 解决方案

### 1. 停止当前运行的程序

如果程序正在运行，按 `Ctrl+C` 停止它。

### 2. 确认没有残留进程

```bash
# 检查是否有残留的Python进程
ps aux | grep sip_ai_nls_optimized
```

如果有，杀掉它们：
```bash
pkill -f sip_ai_nls_optimized
```

### 3. 重新启动程序

```bash
./call_optimized.sh <电话号码>
```

## 验证修复

启动后你应该看到：

### ✅ 正确的启动信息
```
======================================================================
  AI对话系统 - NLS优化版（长连接）
======================================================================
  特性: WebSocket长连接复用，极速ASR/TTS
  回声消除: 已启用 (400ms尾长)
  智能打断: 已启用 (最少15帧, LLM语义:禁用)
======================================================================
  [ASR] 预获取Token...
  [ASR] Token: xxxxx...
  [ASR] 预创建recognizer...
  [ASR] Recognizer创建成功
  [TTS] 预获取Token...
  [TTS] Token: xxxxx...
  [TTS] 预创建synthesizer...
  [TTS] Synthesizer创建成功
```

### ✅ 不应该再看到
```
❌ 'OptimizedNLSASREngine' object has no attribute 'max_errors'
❌ 'OptimizedNLSASREngine' object has no attribute 'error_count'
❌ Must call start before send!  (除非真的有网络问题)
```

## 代码验证

我已经验证过代码是正确的：
```bash
$ python3 check_version.py
✅ min_interval = 1.0
✅ error_count = 0
✅ max_errors = 3

所有属性都已正确初始化！
```

## 为什么需要重启？

Python是解释型语言，但：
1. **启动时加载** - 程序启动时，Python将 `.py` 文件加载到内存
2. **内存中运行** - 运行的是内存中的代码，不是磁盘上的文件
3. **不会自动重载** - 修改文件后，内存中的代码不会自动更新
4. **必须重启** - 只有重启程序，才会重新加载新的代码

## 快速检查列表

- [ ] 停止当前运行的程序（Ctrl+C）
- [ ] 检查没有残留进程（`ps aux | grep sip_ai_nls`）
- [ ] 重新启动（`./call_optimized.sh <号码>`）
- [ ] 验证启动信息正确
- [ ] 进行测试通话
- [ ] 确认不再出现属性错误

## 如果重启后仍有问题

可能的原因：
1. **缓存的 .pyc 文件** - 删除它们：
   ```bash
   find /home/henry/pjproject -name "*.pyc" -delete
   find /home/henry/pjproject -name "__pycache__" -type d -exec rm -rf {} +
   ```

2. **多个Python版本** - 确认使用 `python3`：
   ```bash
   which python3
   python3 --version
   ```

3. **错误的文件** - 确认编辑的是正确的文件：
   ```bash
   ls -lh /home/henry/pjproject/sip_ai_nls_optimized.py
   ```

## 测试建议

重启后，进行一次完整的通话测试：
1. 拨打电话
2. 等待TTS播放
3. 说话测试ASR
4. 测试打断功能
5. 进行多轮对话
6. 观察日志，确认无错误

## 总结

✅ **代码没有问题** - 所有修复都已正确应用
⚠️ **需要重启程序** - 让Python重新加载新代码
🎯 **重启后应该正常** - 不会再有属性错误
